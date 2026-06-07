import type { Character, Project, Relationship, Scene } from './types'

export const sampleNovel = `第一章 雨夜来信

暴雨把临江市洗成一片模糊的霓虹。记者林墨推开旧城区“留声”咖啡馆的门时，老板周岚正准备熄灯。她没有像往常一样打招呼，只朝最里面的位置看了一眼。

桌上压着一封没有署名的信。信里只有一句话：“十二年前沉入江底的，不止一辆车。”

林墨抬头追问，周岚却说自己什么也不知道。门外，一把黑伞在雨幕里停了片刻，又悄无声息地离开。

第二章 消失的底片

林墨回到报社档案室，翻出十二年前临江大桥事故的旧卷宗。当年的摄影记者正是他的父亲林国成，而卷宗里唯独少了现场底片。

实习生苏禾发现借阅记录被人改过，最后一个真实签名指向已退休的刑警陈望。两人赶到陈望住处，却发现门锁被撬，屋里一片狼藉。

陈望从暗处出现，手里握着一卷发黄的底片。他警告林墨：真相会让很多人失去现在拥有的一切。

第三章 桥下之约

午夜，陈望约林墨和苏禾在临江大桥下见面。底片显示，事故发生前，一辆市政工程车曾停在桥中央，而当时负责项目验收的人正是如今的副市长高启明。

周岚突然赶来。她承认匿名信是自己留下的，因为事故中失踪的乘客是她的姐姐。她等待了十二年，只为有人愿意把故事写出来。

远处传来车辆急刹的声音。陈望把底片塞给林墨，让他带着苏禾离开。林墨看着桥上的灯，第一次明白父亲当年没有发表报道的原因。

第四章 天亮之前

林墨决定在天亮前发布调查报道。苏禾负责扫描底片，周岚联系当年的乘客家属，陈望则提供被隐藏的调查笔录。

高启明打来电话，提出用父亲的名誉交换沉默。林墨短暂犹豫后按下录音键，告诉对方：“有些故事迟到了，但不会消失。”

清晨六点，报道上线。城市在晨光中苏醒，临江大桥第一次因为真相而拥堵。周岚站在咖啡馆门口，看见雨停了。`

export const demoCharacters: Character[] = [
  { id: 'char-1', name: '林墨', role: '主角 · 调查记者', description: '执着、敏锐，背负父亲未竟的报道。', color: '#e15d3f' },
  { id: 'char-2', name: '周岚', role: '关键证人 · 咖啡馆老板', description: '克制而坚定，等待真相十二年。', color: '#587a6a' },
  { id: 'char-3', name: '苏禾', role: '搭档 · 实习记者', description: '行动力强，擅长从细节中寻找突破口。', color: '#d09a3e' },
  { id: 'char-4', name: '陈望', role: '知情人 · 退休刑警', description: '沉默谨慎，保管着事故的关键证据。', color: '#657792' },
  { id: 'char-5', name: '高启明', role: '对立人物 · 副市长', description: '试图维持体面与既得利益。', color: '#66576d' },
]

export const demoRelationships: Relationship[] = [
  { from: '林墨', to: '苏禾', relation: '记者搭档' },
  { from: '林墨', to: '周岚', relation: '调查者 / 委托人' },
  { from: '林墨', to: '陈望', relation: '父辈秘密的继承者' },
  { from: '周岚', to: '高启明', relation: '追责者 / 被追责者' },
]

export const demoScenes: Scene[] = [
  {
    id: 'SC-01',
    chapterId: 'chapter-1',
    sourceChapter: '第一章 雨夜来信',
    title: '雨夜的匿名信',
    location: '旧城区 · 留声咖啡馆',
    time: '夜 / 暴雨',
    atmosphere: '安静、潮湿、暗藏不安',
    characters: ['林墨', '周岚'],
    content: [
      { id: 'c-1', type: 'action', action: '林墨收起滴水的黑伞，推开即将打烊的咖啡馆。' },
      { id: 'c-2', type: 'dialogue', action: '林墨拿起没有署名的信，抬眼看向周岚。', character: '林墨', emotion: '疑惑', line: '这是留给我的？' },
      { id: 'c-3', type: 'dialogue', action: '周岚避开他的视线，只朝最里面的桌子看了一眼。', character: '周岚', emotion: '克制', line: '我只负责让你看到它。' },
      { id: 'c-4', type: 'dialogue', action: '林墨攥紧信纸，门外的黑伞在雨幕中停顿。', character: '林墨', emotion: '警觉', line: '十二年前，到底发生了什么？' },
    ],
    sourceSummary: '林墨在雨夜咖啡馆收到匿名信，得知十二年前的大桥事故另有隐情。',
  },
  {
    id: 'SC-02',
    chapterId: 'chapter-2',
    sourceChapter: '第二章 消失的底片',
    title: '被改写的借阅记录',
    location: '临江日报 · 地下档案室',
    time: '深夜',
    atmosphere: '逼仄、陈旧、步步逼近',
    characters: ['林墨', '苏禾'],
    content: [
      { id: 'c-5', type: 'action', action: '苏禾用手电扫过一排排落灰的卷宗。' },
      { id: 'c-6', type: 'action', action: '林墨发现父亲当年的事故档案中少了一袋底片。' },
      { id: 'c-7', type: 'dialogue', action: '苏禾指向电脑屏幕上被覆盖过的借阅记录。', character: '苏禾', emotion: '笃定', line: '记录可以改，但时间戳不会说谎。' },
      { id: 'c-8', type: 'dialogue', action: '林墨盯着闪烁的最后一行记录，压低声音。', character: '林墨', emotion: '低声', line: '有人比我们更怕找到这些底片。' },
    ],
    sourceSummary: '林墨和苏禾在档案室发现底片失踪，并锁定退休刑警陈望。',
  },
  {
    id: 'SC-03',
    chapterId: 'chapter-3',
    sourceChapter: '第三章 桥下之约',
    title: '桥下的底片',
    location: '临江大桥 · 桥下',
    time: '午夜',
    atmosphere: '空旷、紧张、真相逼近',
    characters: ['林墨', '苏禾', '陈望', '周岚'],
    content: [
      { id: 'c-9', type: 'action', action: '陈望迎着江风展开底片，工程车的轮廓在灯下显现。' },
      { id: 'c-10', type: 'dialogue', action: '陈望按住被风吹动的底片，看向林墨。', character: '陈望', emotion: '沉重', line: '你父亲不是不敢写，他是在等证据。' },
      { id: 'c-11', type: 'dialogue', action: '周岚从桥墩后走出，第一次说出姐姐的名字。', character: '周岚', emotion: '坚定', line: '我等了十二年，不想再等下一个十二年。' },
      { id: 'c-12', type: 'action', action: '远处车灯突然亮起，急刹声划破江面。' },
    ],
    sourceSummary: '众人在桥下确认事故与工程车有关，周岚坦白匿名信由她寄出。',
  },
  {
    id: 'SC-04',
    chapterId: 'chapter-4',
    sourceChapter: '第四章 天亮之前',
    title: '迟到的故事',
    location: '临江日报 · 编辑部',
    time: '黎明前',
    atmosphere: '急迫、克制、迎向光亮',
    characters: ['林墨', '苏禾', '高启明'],
    content: [
      { id: 'c-13', type: 'action', action: '扫描仪吐出最后一张底片，上传进度停在百分之九十九。' },
      { id: 'c-14', type: 'dialogue', action: '电话响起，高启明的声音从免提中传出。', character: '高启明', emotion: '冷静', line: '你父亲的名字，也会和这篇报道一起被毁掉。' },
      { id: 'c-15', type: 'dialogue', action: '林墨看着屏幕上的陌生号码，按下录音键。', character: '林墨', emotion: '坚定', line: '有些故事迟到了，但不会消失。' },
      { id: 'c-16', type: 'action', action: '清晨六点，发布按钮由灰色变为红色。' },
    ],
    sourceSummary: '林墨拒绝交易，在天亮前发布了揭露真相的调查报道。',
  },
]

export const defaultProject: Project = {
  title: '雨夜来信',
  filename: '雨夜来信.txt',
  rawText: sampleNovel,
  genre: '都市悬疑',
  style: '克制、写实、电影感',
  era: '当代 · 临江市',
  summary: '一封雨夜匿名信，让记者林墨重新调查十二年前的大桥事故。随着失踪底片与旧调查笔录浮出水面，他不得不在父亲的名誉、现实的威胁与迟到的真相之间作出选择。',
  adaptationMode: '影视化增强',
  scriptType: '短剧',
  dialogueDensity: '密集',
  targetSceneCount: 4,
  chapters: [],
  characters: demoCharacters,
  relationships: demoRelationships,
  scenes: demoScenes,
  updatedAt: new Date().toISOString(),
  revision: 0,
  analysisStatus: 'completed',
  analysisMode: 'demo',
  analysisError: '',
  analysisAttempts: 0,
  generationStatus: 'completed',
  generationMode: 'demo',
  generationError: '',
  generationAttempts: 0,
  generationChapters: [
    { chapter_id: 'chapter-1', status: 'completed', mode: 'demo', attempts: 0, error: '', scene_count: 1 },
    { chapter_id: 'chapter-2', status: 'completed', mode: 'demo', attempts: 0, error: '', scene_count: 1 },
    { chapter_id: 'chapter-3', status: 'completed', mode: 'demo', attempts: 0, error: '', scene_count: 1 },
    { chapter_id: 'chapter-4', status: 'completed', mode: 'demo', attempts: 0, error: '', scene_count: 1 },
  ],
}
