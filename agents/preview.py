from dataclasses import dataclass

@dataclass
class PreviewState:
    record: dict
    confirmed: bool = False
    def render(self) -> str:
        lines = [f"- {k}: {v if v not in (None, '') else '[belum disebutkan]'}" for k, v in self.record.items()]
        return "Preview data:\n" + "\n".join(lines) + "\n\nApakah data ini sudah benar dan siap disimpan? (Ya/Tidak)"

def is_confirmation(text: str) -> bool:
    return text.strip().lower() in {"ya", "iya", "yes", "y", "setuju", "benar"}
