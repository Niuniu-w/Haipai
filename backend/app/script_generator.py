import re

from .schemas import Chapter, Character, Dialogue, Scene

sentence_pattern = re.compile(r"[^。！？\n]+[。！？](?:[”’」』])?|[^。！？\n]+$")
quote_pattern = re.compile(r"“([^”]{1,120})”")
chapter_prefix_pattern = re.compile(r"^(第[零一二三四五六七八九十百\d]+章|Chapter\s+\d+)", re.IGNORECASE)
location_keywords = (
    "咖啡馆",
    "档案室",
    "编辑部",
    "办公室",
    "学校",
    "医院",
    "桥下",
    "大桥",
    "车站",
    "街道",
    "家中",
    "客厅",
    "房间",
)


def split_sentences(content: str) -> list[str]:
    return [sentence.strip() for sentence in sentence_pattern.findall(content) if sentence.strip()]


def infer_location(content: str) -> str:
    return next((keyword for keyword in location_keywords if keyword in content), "待定地点")


def infer_time(content: str) -> str:
    for keyword in ("午夜", "深夜", "夜晚", "夜", "清晨", "黎明", "傍晚", "黄昏", "午后", "白天"):
        if keyword in content:
            return keyword
    return "待定时间"


def infer_atmosphere(genre: str, style: str) -> str:
    if genre == "悬疑":
        return "紧张、克制、暗藏悬念"
    if genre in {"奇幻", "科幻"}:
        return "神秘、富有视觉冲击"
    return style or "写实、人物驱动"


def extract_dialogues(content: str, character_names: list[str], scene_index: int) -> list[Dialogue]:
    dialogues: list[Dialogue] = []
    for quote_index, match in enumerate(quote_pattern.finditer(content)):
        prefix = content[: match.start()]
        speaker = max(character_names, key=prefix.rfind) if character_names else "角色"
        if character_names and prefix.rfind(speaker) < 0:
            speaker = character_names[quote_index % len(character_names)]
        dialogues.append(
            Dialogue(
                id=f"dialogue-{scene_index + 1}-{quote_index + 1}",
                character=speaker,
                emotion="平静",
                line=match.group(1),
            )
        )
    return dialogues[:4]


def build_local_scenes(
    chapters: list[Chapter],
    characters: list[Character],
    genre: str,
    style: str,
) -> list[Scene]:
    scenes: list[Scene] = []
    for index, chapter in enumerate(chapters):
        sentences = split_sentences(chapter.content)
        character_names = [character.name for character in characters if character.name in chapter.content]
        dialogues = extract_dialogues(chapter.content, character_names, index)
        title = chapter_prefix_pattern.sub("", chapter.title).strip() or f"场景 {index + 1}"
        scenes.append(
            Scene(
                id=f"SC-{index + 1:02d}",
                chapterId=chapter.id,
                sourceChapter=chapter.title,
                title=title,
                location=infer_location(chapter.content),
                time=infer_time(chapter.content),
                atmosphere=infer_atmosphere(genre, style),
                characters=character_names,
                actions=sentences[:3] or ["根据原文章节补充动作描述。"],
                dialogues=dialogues,
                sourceSummary=chapter.summary,
            )
        )
    return scenes
