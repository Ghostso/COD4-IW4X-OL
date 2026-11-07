#!/usr/bin/env python3
"""压缩 MEMORY.md 的 132/133/135/136 四条(细节已在各自 topic 文件)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

NEW = {
    "- [★★★★★ AS面静态收口": "- [★★★★★ AS面静态收口+825注册器+62回调全表(136)](codol-as-static-closure-136.md) — ★★★纯静态收口。①**真注册器=825(精确)**：判据换**双向有界**(`[入口,首ret)`内有`push <短名>`)⇒828里**恰好3条非注册器**(`0x6A7650`/`0x6AEBD0`/`0x728350`)；★135的「≤825」真因=我的`cstr(maxlen=40)`截断了4个长名(最长49字符)。②★★★**7个View的62个Flash回调全表**(UiCppView3/MatchSelectView28/ItemListView11/Onboarding6/SuggestedLoadout5/Challenges5/NewItems4)；★`AS_*`=Flash调C++、`On*Click`/`On*Change`=C++调Flash(同一Scaleform面两方向)；补齐130/131悬了四卷的UI面名字。③★★★**三方互证62=28+11+6+5+5+4+3**(RTTI名⊗分批函数注册器数⊗132计数)⇒View注册站点=7个分批函数(基类三件套=`0x7396F0`)。④`?<n>`=**`Init`内全部局域类型声明序**(跨View重复⇒非全局；最大337而handler仅28)；★地址上倒挂。⑤★★**`and eax,0x8F`=全局值类型判据**(2801处,值域`{0xA:2457,9,6,5,1}`)；★类型名「这里没有」(AS3 VM类无RTTI:Interpreter/Movie/Sprite/Loader/GFxPlayer/AVMP/ASVM全0)。⑥10个「非唯一调用者」=8个跨容器注册(如`AS_IsInClan`×3)+2个非注册器。⑦★★**注册器身份机械闭环**：`vtable[-1]`(COL)→`ti+8`→**RTTI名=`AS_<短名>`**；★★精确化133/135：ctor写`Scaleform::RefCountImplCore`+`[+4]=1`=**refcount**、**dtor shim才写`GFx::FunctionHandler`**(两卷混称「父类vptr」)⇒`as_name_to_vtable.json`获结构侧独立交叉验证。⑧`[0xc77bb98]`创建点=`0x5EB9D0`→`manager->vt[0x60]`(`0x4F70A0`)、销毁=`0x5ED804`；`GFx::Value`=20字节。★方法论**「未找到」先查自己的过滤器常数**、**判据两端都要有界才能给精确值**、**异质互证才算互证**、**用「重复值」否证「索引假设」**、**「未定」要分「没找到」与「这里没有」**、**vtable反查类名把模糊词变精确**",
    "- [★★★★★ AS注册链三层归属": "- [★★★★★ AS注册链三层归属+GFx转发器表(135)](codol-as-registration-3layer-135.md) — ★★★机制层收口+更正134两条。①**三层**：`0x5ED010`(一次性AS初始化,载`scaleform/default/codo.gfx`)→3容器主函数(`0x5EBB00`/`0x5EBB90`/`0x5EBDD0`)→分批函数(`0x5EBB90`体内44个E8)→828单名注册器；`[0xc77bb98]`=Scaleform全局单例。②★★**3个AS3容器类名**(各恰好1引用)：`codo.common.CFunctionCommonContainer`/`CFunctionContainer`/`CFunctionInGameContainer`@`0xDC418C/41B4/41D4`。③★★**名字→对象映射的肯定式答案**：容器=`0x730690`里`0x830B00(global,\"flash.utils.getDefinitionByName\")`**反射取到的AS3类对象**,注册器往它身上**定义属性**⇒**表在SWF/AS3运行时**(133「表不存在」升级)。④注册器模板`[[edi+8]]->vt[0x14]([edi+0x10],\"JoinRoom\",&Value16,bool((容器.flags&0x8F)==0x0A))`。⑤★★**GFx转发器thunk表**`0x830AC0..0x830BC0`9个17字节(`mov ecx,[ecx+0xC];...jmp eax`),slot∈`{0xB0..0xC8,0xE4,0xE8}`⇒**闭掉133/134连抄两卷的「0x830BC0容器语义未解」**。⑥分批函数序言`57 8b f8 56`。⑦归属347/217/94/28/25。⑧★★**更正134 §⑤**：`0x6AEBD0`=分批函数、`0x728350`=惰性初始化,**都不是注册器**(真因=134的「体内前0x300字节」窗口**向下跨函数**)。★方法论**判据窗口须双向设防**、**同形字节模板=族指纹**、**数量差异先问口径**、**「未解」会传染**",
    "- [★★★★★ AS注册链全闭合": "- [★★★★★ AS注册链全闭合+816短名全表+AS_DMZ(133)](codol-as-registration-chain-133.md) — ★★★**「名字→对象表」根本不存在**：每接口一个0xB9字节注册器,体内`mov [eax],<vtable>`+`push <短名>`+`call [edx+0x14]`三者焊死；判据=**vtable的立即数写入位置**⇒838(135/136修正为828候选/**825真**)；**816短名↔829对象已导表**`tools/as_name_to_vtable.json`；62个`?N@`局域类同路径；`0x73DF20`调28次≡132的28；★★**`AS_DMZ_*`整簇9个⇒撤离模式UI齐备**⇒修正「PvE整体不完整」(剧情缺≠DMZ缺)；★方法论**「找不到X」先问X该不该存在**、**找注册器用行为指纹**、**「找到N个」必配「多少无归属」**、**同一缺口≥3次即查预设**",
    "- [★★★★★ AS对象结构定案": "- [★★★★★ AS对象结构定案+829族谱+UiCppInit注册关系(132)](codol-as-vtable-829-objects-132.md) — ★★**闭掉131§十三**：真结构`[COL][vf0=0x693DD0][vf1=handler]`**17字节步进**(131按12⇒每4个错位一格,「两读法都通」是同一窗口两种切法)；判据`vftable[-1]`须是合法COL+槽须是代码；**全量829个**；`0x8435E0`被**22个对象**共用⇒**运营面整体关闭**；★★★**63个对象RTTI名自带`?N@??Init@UiCppXxx@@`**⇒注册关系零猜测(136把回调名全部列出)；`OnRoomsListed`/`OnRoomListExpired`=21/5 findSessions的Flash接收端(协议面与UI面首次接通)；★方法论**结构长度须自证**、**两理论都通时查共享前提**、**数量必`len(list)`不能数打印行**",
}

lines = io.open(P, encoding="utf-8").read().split("\n")
repl = 0
for i, ln in enumerate(lines):
    for pref, txt in NEW.items():
        if ln.startswith(pref):
            lines[i] = txt
            repl += 1
            break
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("替换 %d 条" % repl)
print("新字节数 %d" % len("\n".join(lines).encode("utf-8")))
