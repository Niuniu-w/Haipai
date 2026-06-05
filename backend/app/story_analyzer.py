import re
from collections import Counter

from .schemas import Chapter, Character, Relationship

colors = ["#e15d3f", "#587a6a", "#d09a3e", "#657792", "#66576d", "#8a6b4f"]
surname_pattern = (
    r"(?:欧阳|司马|上官|诸葛|"
    r"[赵钱孙李周吴郑王冯陈蒋沈韩杨朱秦许何吕张曹金魏姜谢邹苏潘范彭鲁韦马方任袁柳唐薛雷贺倪汤罗郝安"
    r"于傅齐康伍余顾孟黄穆萧尹姚邵汪毛米贝戴宋熊舒祝董梁杜阮蓝季贾江童郭梅林钟徐邱骆高夏蔡田樊胡"
    r"霍万卢莫房解丁邓洪包左石崔龚程陆白龙叶黎文])"
)
name_pattern = rf"{surname_pattern}[\u4e00-\u9fff]{{1,2}}"
role_pattern = re.compile(
    rf"(记者|老板|实习生|刑警|副市长|警察|医生|老师|学生|律师|侦探|父亲|母亲|姐姐|哥哥)"
    rf"({name_pattern})(?=在|说|问|答|看|走|来|去|收到|发现|决定|回到|推开|赶到|出现|警告|负责|联系|打来|站在|"
    rf"抬头|突然|承认|等待|拿起|告诉|约|离开|拒绝|正|却|则|，|。|！|？|、|：|:|\s)"
)
action_pattern = re.compile(
    rf"({name_pattern})(?=在|说|问|答|看|走|来|去|收到|发现|决定|回到|推开|赶到|出现|警告|负责|联系|打来|站在|"
    rf"抬头|突然|承认|等待|拿起|告诉|约|离开|拒绝|把|却|则)"
)
sentence_pattern = re.compile(r"[。！？](?:[”’」』])?|\n")
name_stopwords = {
    "第一章",
    "第二章",
    "第三章",
    "第四章",
    "当年的",
    "如今的",
    "自己的",
    "他们",
    "我们",
    "有人",
    "很多人",
    "真相",
    "城市",
    "事故",
    "故事",
}


def infer_genre(text: str) -> str:
    keyword_groups = [
        ("悬疑", ("调查", "真相", "秘密", "失踪", "案件", "证据", "警告")),
        ("科幻", ("星际", "宇宙", "机器人", "未来", "人工智能", "飞船")),
        ("奇幻", ("魔法", "精灵", "龙族", "异世界", "法师")),
        ("古装", ("皇帝", "王爷", "江湖", "朝廷", "将军", "宫中")),
        ("都市情感", ("爱情", "恋爱", "婚姻", "相亲", "前任")),
    ]
    scores = [(genre, sum(text.count(keyword) for keyword in keywords)) for genre, keywords in keyword_groups]
    genre, score = max(scores, key=lambda item: item[1])
    return genre if score else "剧情"


def infer_era(text: str) -> str:
    if any(keyword in text for keyword in ("皇帝", "王爷", "朝廷", "宫中", "江湖")):
        return "古代"
    if any(keyword in text for keyword in ("未来", "星际", "宇宙", "飞船")):
        return "未来"
    return "当代"


def infer_style(genre: str) -> str:
    return {
        "悬疑": "紧凑、克制、悬念驱动",
        "科幻": "宏大、想象力丰富、视觉化",
        "奇幻": "神秘、冒险、世界观驱动",
        "古装": "厚重、含蓄、戏剧化",
        "都市情感": "细腻、现实、人物驱动",
    }.get(genre, "写实、流畅、人物驱动")


def extract_characters(chapters: list[Chapter]) -> list[Character]:
    text = "\n".join(chapter.content for chapter in chapters)
    roles: dict[str, str] = {}
    candidates: list[str] = []

    for role, name in role_pattern.findall(text):
        roles[name] = role
        candidates.append(name)
    candidates.extend(action_pattern.findall(text))

    unique_names = {name for name in candidates if name not in name_stopwords and 2 <= len(name) <= 4}
    counts = Counter({name: text.count(name) for name in unique_names})
    characters: list[Character] = []
    for index, (name, _) in enumerate(counts.most_common(6)):
        sentences = [sentence.strip() for sentence in sentence_pattern.split(text) if name in sentence]
        description = sentences[0][:60] if sentences else f"{name}是故事中的重要人物。"
        role = roles.get(name, "主要人物" if index < 3 else "关键人物")
        characters.append(
            Character(
                id=f"char-{index + 1}",
                name=name,
                role=role,
                description=description,
                color=colors[index % len(colors)],
            )
        )
    return characters


def extract_relationships(chapters: list[Chapter], characters: list[Character]) -> list[Relationship]:
    if len(characters) < 2:
        return []

    core = characters[0].name
    relationships: list[Relationship] = []
    for character in characters[1:5]:
        shared_chapters = sum(core in chapter.content and character.name in chapter.content for chapter in chapters)
        if shared_chapters:
            relationships.append(
                Relationship(
                    **{
                        "from": core,
                        "to": character.name,
                        "relation": f"共同出现在 {shared_chapters} 个章节",
                    }
                )
            )
    return relationships


def build_summary(title: str, chapters: list[Chapter]) -> str:
    chapter_summaries = [chapter.summary for chapter in chapters if chapter.summary]
    if not chapter_summaries:
        return f"《{title}》包含 {len(chapters)} 个章节，故事分析结果等待补充。"
    joined = "；".join(chapter_summaries[:3])
    return f"《{title}》围绕以下故事线展开：{joined}。"


def analyze_story(title: str, chapters: list[Chapter]) -> dict:
    text = "\n".join(chapter.content for chapter in chapters)
    genre = infer_genre(text)
    characters = extract_characters(chapters)
    return {
        "summary": build_summary(title, chapters),
        "genre": genre,
        "era": infer_era(text),
        "style": infer_style(genre),
        "characters": characters,
        "relationships": extract_relationships(chapters, characters),
        "chapters": chapters,
    }
