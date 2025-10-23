import json
from typing import List, Dict, Any

from PIL import Image

try:
    from transformers import DonutProcessor, VisionEncoderDecoderModel
except Exception:  # pragma: no cover
    DonutProcessor = None  # type: ignore
    VisionEncoderDecoderModel = None  # type: ignore

try:  # device support
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore


_MODEL_NAME = "naver-clova-ix/donut-base-finetuned-cord-v2"


class DonutUnavailable(Exception):
    pass


def _load_donut():
    if DonutProcessor is None or VisionEncoderDecoderModel is None:
        raise DonutUnavailable("transformers not installed")
    try:
        processor = DonutProcessor.from_pretrained(_MODEL_NAME)
    except Exception as e:
        # Most common: sentencepiece missing for the tokenizer
        raise DonutUnavailable(f"processor load failed: {e}")
    try:
        model = VisionEncoderDecoderModel.from_pretrained(_MODEL_NAME)
    except Exception as e:
        raise DonutUnavailable(f"model load failed: {e}")
    model.eval()
    # Move to GPU if available
    if torch is not None and torch.cuda.is_available():
        model.to('cuda')
        try:
            model.half()
        except Exception:
            pass
    return processor, model


def parse_receipt_with_donut(image_path: str) -> Dict[str, Any]:
    """
    Returns dict with keys:
      - items: list[{name, quantity, unit?, price?}]
      - raw: raw JSON string produced by the model (if any)
    Raises DonutUnavailable if transformers are missing.
    """
    processor, model = _load_donut()

    image = Image.open(image_path).convert("RGB")
    task_prompt = "<s_cord-v2>"
    inputs = processor(image, return_tensors="pt")
    prompt_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
    device = 'cuda' if (torch is not None and torch.cuda.is_available()) else 'cpu'
    if torch is not None:
        inputs = {k: v.to(device) for k, v in inputs.items()}
        prompt_ids = prompt_ids.to(device)
    with torch.no_grad() if torch is not None else _nullcontext():
        output_ids = model.generate(
            inputs["pixel_values"],
            decoder_input_ids=prompt_ids,
            max_length=model.config.decoder.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    seq = processor.batch_decode(output_ids.sequences)[0]
    seq = seq.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
    # processor.token2json converts the generated string to a JSON structure
    data = processor.token2json(seq)

    items: List[Dict[str, Any]] = []
    # CORD schema commonly under data["receipt"]["items"]
    try:
        receipt = data.get("receipt") or {}
        lines = receipt.get("items") or []
        for line in lines:
            name = (line.get("item_name") or "").strip()
            qty = line.get("count") or line.get("qty") or line.get("quantity")
            price = line.get("item_price") or line.get("price") or line.get("amount")
            unit = None
            # Attempt to parse qty like "2 kg" or "1.5 l" or "12 pcs"
            if isinstance(qty, str):
                parts = qty.strip().split()
                if parts:
                    try:
                        q = float(parts[0].replace(",", "."))
                    except Exception:
                        q = None
                    if q is not None:
                        unit = parts[1].lower() if len(parts) > 1 else None
                        qty = q
            try:
                quantity = float(qty)
            except Exception:
                quantity = 1.0
            try:
                price_val = float(str(price).replace(",", "")) if price is not None else None
            except Exception:
                price_val = None
            if name:
                items.append({
                    "name": name,
                    "quantity": quantity,
                    "unit": unit or "",
                    "price": price_val,
                })
    except Exception:
        # If structure unexpected, just return raw
        pass

    return {"items": items, "raw": json.dumps(data, ensure_ascii=False)}


# Minimal context manager when torch is unavailable
class _nullcontext:
    def __enter__(self):
        return None
    def __exit__(self, exc_type, exc, tb):
        return False
