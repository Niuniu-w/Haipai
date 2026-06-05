import re

from .schemas import Chapter

chapter_pattern = re.compile(
    r"^(第[零一二三四五六七八九十百\d]+章[^\n。！？]{0,80}|Chapter\s+\d+[^\n.!?]{0,80})$",
    re.IGNORECASE | re.MULTILINE,
)
sentence_pattern = re.compile(r"[。！？](?:[”’」』])?|\n")


def parse_chapters(text: str) -> list[Chapter]:
    matches = list(chapter_pattern.finditer(text))
    chapters: list[Chapter] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sentences = [sentence.strip() for sentence in sentence_pattern.split(content) if sentence.strip()]
        chapters.append(
            Chapter(
                id=f"chapter-{index + 1}",
                title=match.group(0).strip(),
                content=content,
                summary="。".join(sentences[:2])[:120],
                keyEvents=sentences[:3],
            )
        )

    return chapters
