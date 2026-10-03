"""Correct English lecture lines and rewrite them as spoken Chinese."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .runtime import backend, cuda_device, default_llm, require_cuda, torch_dtype
from .subtitles import Cue, speakable_units

DEFAULT_LLM = "mlx-community/Qwen3-8B-4bit"

PROMPT = """你是大学课堂的中文配音译员。输入是英文字幕片段。请完成两件事：
1. 修正明显的听写错误，专有名词按计算机系统课的通行写法。没有明显错误就保持英文原句。
2. 写成能直接念出来的简体中文口播。像老师在课堂上讲，口语自然，不要书面腔，不要加“翻译、字幕、注”这类话。

准确性：
- 不要补充原句没有的知识，不要删掉数字、结论、系统名和条件。
- 英文字幕是自动生成的，会听错词，也会把否定听反。先看 prev 和 next，把当前句改成老师真正在讲、并且和前后都能对上的意思，再翻译。
- 如果当前句和前后矛盾，以能让这几句同时成立的意思为准。例如后面说到 both rooms、either of the rooms，there isn't two classrooms 要改成 there are two classrooms，中文说有两个考场。
- 不要把听错的词当成专有名词。Homework Day was due 按“作业周日已经截止”来讲，不要译成“作业日”。
- 听写错误要按课程改对，例如 heart beating 是心跳，gossip cell heart beating 是 Gossip 式心跳，impossibility result 是不可能性结果。
- next 只用来消歧。中文不要把下一句提前说出来。英文如果没有句号或问号，中文就停在同样的地方，结尾用逗号，不要把 next 补完。
- 英文里的每个分句都要译出来，不要只翻译前半句。
- 系统名和缩写保留英文：Raft、Paxos、MapReduce、GFS、Bigtable、Spanner、Dynamo、Kafka、Pregel、Snowflake、System R、C-Store、Dremel、SQL、CPU、RPC、WAL、FLP、P2P。
- 术语用下面的译法，全课保持一致：failure detector 故障检测器，completeness 完备性，accuracy 准确性，heartbeat 心跳，membership 成员关系，peer-to-peer 对等网络，quorum 多数派，leader election 选主，replication 副本复制，consensus 共识，partition 分区，consistency 一致性，availability 可用性，latency 延迟，throughput 吞吐，transaction 事务，commit 提交，query optimizer 查询优化器，columnar 列式存储，materialized view 物化视图，checkpoint 检查点，write-ahead log 预写日志，shard 分片，asynchronous 异步。
- 每条中文的口语长度不要超过 max_chars。太长就压缩，太短不要为了凑字数加废话。
- prev 是上一句，仅供你看懂残句。中文只讲当前这句，不要把上一句重说一遍。
- 只输出一个 JSON 数组，不要解释，不要 Markdown。

输入：
{payload}

输出格式：
[{{"id": 1, "en": "修正后的英文", "zh": "中文口播"}}]
"""


@dataclass
class Line:
    id: int
    start: float
    end: float
    en: str
    zh: str

    @property
    def seconds(self) -> float:
        return max(0.4, self.end - self.start)


def _strip_thinking(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = text.replace("<think>", "").replace("</think>", "")
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def _parse_array(text: str) -> list[dict]:
    cleaned = _strip_thinking(text)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("model did not return a JSON array")
    data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("model JSON was not a list")
    return data


def _sanitize(text: str) -> str:
    text = text.strip().strip("“”\"'")
    text = re.sub(r"^(中文|译文|口播)\s*[:：]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


class Translator:
    def __init__(self, model_id: str = DEFAULT_LLM):
        self.model_id = model_id
        if backend() == "mlx":
            from mlx_lm import load

            self.model, self.tokenizer = load(model_id)
            self._backend = "mlx"
            return
        if model_id.startswith("mlx-community/"):
            self.model_id = default_llm()
        self._backend = "cuda"
        self.model, self.tokenizer = _load_cuda_llm(self.model_id)

    def complete(self, user: str, max_tokens: int) -> str:
        messages = [{"role": "user", "content": user}]
        try:
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        if self._backend == "mlx":
            from mlx_lm import generate

            return generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,
            )
        return _cuda_generate(self.model, self.tokenizer, prompt, max_tokens)

    def translate_batch(self, items: list[dict]) -> dict[int, dict]:
        prompt = PROMPT.format(payload=json.dumps(items, ensure_ascii=False))
        raw = self.complete(prompt, max_tokens=max(900, 280 * len(items)))
        rows = _parse_array(raw)
        found: dict[int, dict] = {}
        for row in rows:
            if "id" not in row or "zh" not in row:
                continue
            found[int(row["id"])] = {
                "en": _sanitize(str(row.get("en") or "")),
                "zh": _sanitize(str(row["zh"])),
            }
        return found

    def shorten(self, english: str, chinese: str, max_chars: int) -> str:
        prompt = (
            "把下面这句课堂口播再压短，意思不变，仍然像老师在说话。"
            f"口语长度不要超过 {max_chars}。只输出压缩后的一句中文。\n"
            f"英文：{english}\n现有中文：{chinese}"
        )
        text = _sanitize(_strip_thinking(self.complete(prompt, max_tokens=180)))
        text = re.sub(r"^[\[{].*", "", text).strip()
        return text or chinese

    def retranslate(self, item: dict, problem: str) -> dict | None:
        prompt = (
            "只重写这一条课堂口播。只输出一个 JSON 对象，不要解释。\n"
            f"必须改掉的问题：{problem}\n"
            "中文要像老师在说话。不要补充原句没有的知识。长度不要超过 max_chars。\n"
            + json.dumps(item, ensure_ascii=False)
        )
        raw = self.complete(prompt, max_tokens=400)
        cleaned = _strip_thinking(raw)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            row = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
        zh = _sanitize(str(row.get("zh") or ""))
        if not zh:
            return None
        return {"en": _sanitize(str(row.get("en") or "")) or item["en"], "zh": zh}


def _load_cuda_llm(model_id: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    require_cuda()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    vram = torch.cuda.get_device_properties(0).total_memory
    kwargs = {"device_map": cuda_device()}
    if vram < 18 * 1024**3:
        try:
            import bitsandbytes  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "This NVIDIA GPU has less than 18 GB. Install bitsandbytes so translation can run in 4-bit, "
                "or set LECTUREDUB_LLM to a 4-bit Qwen3 checkpoint."
            ) from exc
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    else:
        kwargs["torch_dtype"] = torch_dtype()
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    return model, tokenizer


def _cuda_generate(model, tokenizer, prompt: str, max_tokens: int) -> str:
    import torch

    device = next(model.parameters()).device
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
        )
    new_tokens = output[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def repair_english(text: str, following: str) -> str:
    """Fix caption errors that are obvious from the next line."""
    nxt = following.lower()
    if re.search(r"isn'?t two classrooms", text, re.I) and re.search(r"\b(both|either)\b", nxt):
        text = re.sub(r"isn'?t two classrooms", "are two classrooms", text, flags=re.I)
    text = re.sub(r"\bHomework Day\b", "the homework", text)
    text = re.sub(r"\bgossip cell heart beating\b", "gossip-style heartbeat", text, flags=re.I)
    text = re.sub(r"\bheart beating\b", "heartbeat", text, flags=re.I)
    return text


def translation_problem(item: dict, zh: str) -> str | None:
    en = item["en"].rstrip()
    nxt = (item.get("next") or "").lstrip()
    if re.search(r"\btwo classrooms\b", en, re.I) and re.search(r"一个(考场|教室)", zh) and "两" not in zh:
        return "这里是两个考场，不是一个。按修正后的英文重译。"
    if (
        en
        and en[-1] not in ".?!"
        and nxt
        and nxt[0].islower()
        and zh.rstrip().endswith(("。", "！", "？"))
        and speakable_units(zh) > item["max_chars"] * 0.5
    ):
        return "英文停在半句，下一句才接。中文只说到这里，不要把下一句补完，结尾用逗号。"
    en_sents = len(re.findall(r"[.!?]", en))
    zh_sents = len(re.findall(r"[。！？]", zh))
    if en_sents >= 2 and zh_sents < en_sents and speakable_units(zh) <= int(item["max_chars"] * 0.85):
        return "英文后面的分句被漏掉了。每一句都要译出来，不要只留前半句。"
    return None


def translate_cues(
    cues: list[Cue],
    translator: Translator,
    *,
    units_per_second: float,
    batch_size: int = 8,
    on_batch=None,
    already: list[Line] | None = None,
    checkpoint=None,
) -> list[Line]:
    pending = []
    previous = ""
    for index, cue in enumerate(cues):
        seconds = max(0.4, cue.end - cue.start)
        following = cues[index + 1].text if index + 1 < len(cues) else ""
        english = repair_english(cue.text, following)
        pending.append(
            {
                "id": index,
                "seconds": round(seconds, 2),
                "max_chars": max(8, int(seconds * units_per_second)),
                "prev": previous[-160:],
                "next": following[:160],
                "en": english,
            }
        )
        previous = english
    translated: dict[int, dict] = {}
    if already:
        for line in already:
            if line.id < len(cues) and abs(cues[line.id].start - line.start) < 0.05 and line.zh:
                translated[line.id] = {"en": line.en, "zh": line.zh}
    todo = [item for item in pending if item["id"] not in translated]
    cursor = 0
    while cursor < len(todo):
        chunk = todo[cursor : cursor + batch_size]
        try:
            got = translator.translate_batch(chunk)
        except (json.JSONDecodeError, ValueError):
            if len(chunk) == 1:
                raise
            midpoint = len(chunk) // 2
            chunk = chunk[:midpoint]
            got = translator.translate_batch(chunk)
        missing = [item for item in chunk if item["id"] not in got or not got[item["id"]]["zh"]]
        if missing:
            got.update(translator.translate_batch(missing))
        for item in chunk:
            row = got.get(item["id"])
            if not row or not row["zh"]:
                row = translator.translate_batch([item]).get(item["id"])
            if not row or not row["zh"]:
                raise RuntimeError(f"translation missing for cue {item['id']}")
            problem = translation_problem(item, row["zh"])
            if problem:
                fixed = translator.retranslate(item, problem)
                if fixed and fixed.get("zh"):
                    row = fixed
            if speakable_units(row["zh"]) > int(item["max_chars"] * 1.45):
                shorter = translator.shorten(item["en"], row["zh"], item["max_chars"])
                if shorter and speakable_units(shorter) >= speakable_units(row["zh"]) * 0.55:
                    row = {**row, "zh": shorter}
            translated[item["id"]] = {
                "en": row["en"] or item["en"],
                "zh": row["zh"],
            }
        cursor += len(chunk)
        if checkpoint is not None:
            rows = []
            for index, cue in enumerate(cues):
                row = translated.get(index)
                if row is None:
                    break
                rows.append(
                    {
                        "id": index,
                        "start": cue.start,
                        "end": cue.end,
                        "en": row["en"],
                        "zh": row["zh"],
                    }
                )
            checkpoint.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        if on_batch:
            on_batch(len(translated), len(pending))

    lines = []
    for index, cue in enumerate(cues):
        row = translated[index]
        lines.append(Line(index, cue.start, cue.end, row["en"], row["zh"]))
    return lines
