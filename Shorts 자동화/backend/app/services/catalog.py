from app.core.config import get_settings
from app.schemas.catalog import Template

# Display copy for each template. Which ones can run is config (templates_available).
_TEMPLATES = [
    ("celeb_item", "연예인 꿀템", "연예인·셀럽이 소개한 제품 구간으로 쇼츠를 만들어요"),
    ("top3", "TOP 3", "여러 제품을 순위로 묶어 소개해요"),
    ("story", "썰 풀기", "제품에 얽힌 이야기를 풀어요"),
]


def list_templates() -> list[Template]:
    available = get_settings().templates_available
    return [
        Template(id=tid, name=name, description=desc, available=tid in available)
        for tid, name, desc in _TEMPLATES
    ]
