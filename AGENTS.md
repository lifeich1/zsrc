# AGENTS.md

本文件会被每个会话自动加载。**先读本文件**：它给出仓库地图与「少读代码」的阅读策略。

## 仓库地图

| 路径 | 内容 | 索引 |
| --- | --- | --- |
| `calory/` | 每日菜单记录与热量计算 CLI（Python 3，零依赖） | [calory/README.md](calory/README.md) |
| `deb/` | Debian CLI 环境（bashrc/vimrc/inputrc/apt.list + Dockerfile） | 目录内文件自解释 |
| `st/` | syncthing 服务（Dockerfile + startup.sh + apt.list） | 同上 |
| `v0/` | 梯子服务（Dockerfile + run.sh） | 同上 |
| `pi/` | 树莓派：systemd 单元与脚本（watch-temp.py、pull-git-bak.sh…） | 同上 |
| `gtr5/` | GTR5 主机配置：vim/emacs/zsh、systemd、pl 脚本 | 同上 |
| `gtr7/` | GTR7 主机配置（目前为空目录，规划中） | — |
| `monkey/` | 油猴用户脚本 | 同上 |
| `openwrt/` | 路由器配置（clash.yaml、add-pkgs.txt、setup 脚本） | 同上 |
| `utils/` | 通用脚本（memo-update、g-visual.pl） | 同上 |
| `ext/` | 外部同步脚本（multi-repo-git-fetch.sh 等） | 同上 |

## 省 context / token 的阅读策略（重要）

1. **先读 README，再读代码。** 进入任何目录先读它的 `README.md`；只有索引没覆盖的细节才去读源码。
2. **分层索引，能停在上一层就别往下钻**：
   仓库根 `AGENTS.md` → 子项目 `README.md` → 子目录 `README.md` → 源码。
   `calory/` 已是这个结构：`calory/calory/README.md`（模块与 API）、`calory/data/README.md`（数据格式）、`calory/tests/README.md`（用例分布）。
3. **不为「了解结构」而通读文件。** 定位符号用 `rg`，读文件用 `offset`/`limit` 读片段，避免整文件读入。
4. **大文件先看索引。** 例如 `calory/tests/test_calory.py` 有 700+ 行，`calory/tests/README.md` 已列出每个测试类的覆盖范围，定位用例看索引即可。
5. **数据文件不逐行读。** 格式见 `calory/data/README.md`；查具体食物用 `cd calory && ./cal food search <关键词>`。
6. **改代码就改索引。** 新增目录必须带 `README.md`；职责、公开 API、数据格式、运行命令变化时，同步更新该目录 README 与本文件地图。**索引过期比没有索引更糟**——宁可不写，也不要写不准确的。

## 目录 README 的写法（新增目录时遵循）

每份 README 面向「需要改代码但不该通读代码的人/助手」，包含四块即可：

- **职责/格式**：目录里有什么、关键文件与公开 API、数据文件字段；
- **不变量与约定**：改之前必须知道的坑（如快照语义、单位换算、依赖方向）；
- **运行方式**：构建/测试/常用命令；
- **改动落点**：常见需求对应改哪个文件。

避免写宣传性内容；只写能替代读代码的信息。

## 约定

- commit message 用 gitmoji：`:emoji: <component>: <desc>`（例：`:sparkles: calory: add calorie tracking cli`），祈使句、≤50 字符。
- `calory/` 只用 Python 标准库，不引入第三方依赖；注释、异常信息与 CLI 输出用中文。
- 数据文件默认纳入 git 便于多设备同步；`.gitignore` 只排除解密后的明文（`/lastpass_export.csv`、`/github-recovery-codes.txt`）与 Python 产物。
- 验证改动：`cd calory && python3 -m unittest discover tests`。

## 常用命令

```bash
cd calory && ./cal --help                            # CLI 用法
cd calory && ./cal show                              # 当天明细与合计
cd calory && python3 -m unittest discover tests      # 全部测试
cd calory && ./cal food search 鸡                     # 查食物库条目
```
