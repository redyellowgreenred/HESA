# MaxCoverage 本轮修改记录

日期：2026-04-23

## 修改背景

这一轮修改的目标，是改善 `MaxCoverage` 在当前 EA 框架下的表现。

前面的实验里已经看到一个比较明显的问题：  
算法虽然能拿到 `fitness`，但如果只按 `fitness` 去保留和更新个体，就可能把一些实际上不满足约束的解也当成“好解”留在种群里。这样会导致两类现象：

- 种群中会长期停留一些不可行但表面分数不差的个体；
- 历史最优解也可能被不可行解污染，导致搜索方向偏掉。

因此，这一版没有继续调简单的惩罚权重，而是把修改重点放在两件事上：

- 对 `MaxCoverage` 引入“可行优先”的保留逻辑；
- 对新生成的不可行子代做轻量级 repair。

## 本次修改内容

### 1. 把 `penalty` 正式接入状态流

文件：

- `ea_phase2_population.py`

具体修改：

- `evaluate_solution(problem, x)` 不再只返回 `fitness` 和 `violation`，而是统一返回：
  - `fitness`
  - `violation`
  - `penalty`
- `PopulationState` 中新增了：
  - `penalties`
  - `best_violation`
  - `best_penalty`

这样做的意义是：  
后续无论是初始化、精英保留、repair，还是更新历史最优，都可以基于同一套约束信息来判断，而不是每个阶段各写一套临时逻辑。

### 2. 新增 `feasible-first` 排序规则

文件：

- `ea_phase2_population.py`

新增函数：

- `is_feasible_penalty(penalty)`
- `solution_sort_key(fitness, violation, penalty, prefer_feasible)`

核心思想：

- 对 `MaxCoverage`，比较两个解时，不再直接只看 `fitness`；
- 而是先判断是否可行；
- 可行解优先于不可行解；
- 在可行解内部，再比较 `fitness`；
- 在不可行解内部，再优先考虑约束更好的解。

这相当于把原来“单一标量打分”的比较方式，改成了“分层比较”的方式。

### 3. 初始化时的最优个体选择同步改为可行优先

文件：

- `ea_phase2_population.py`

以前初始化后直接用：

```python
best_idx = int(np.argmax(fitnesses))
```

现在改成基于 `solution_sort_key(...)` 选最优个体。  
这意味着对 `MaxCoverage` 来说，初始阶段记录下来的 `best_x / best_y` 也会优先偏向可行解。

### 4. 精英保留改成 `feasible-first survival`

文件：

- `ea_phase5_survival.py`

具体修改：

- `select_elite_survivors(...)` 现在多接收一个 `penalties`
- 同时新增参数 `prefer_feasible`
- 排序时调用统一的 `solution_sort_key(...)`

修改后的效果是：

- `MaxCut` 仍然按原来的思路工作；
- `MaxCoverage` 在保留精英个体时，会优先保留可行解。

也就是说，这一版真正改变的是“谁能活到下一代”。

### 5. 为 `MaxCoverage` 子代加入轻量级 repair

文件：

- `main.py`

新增函数：

- `repair_maxcoverage_child(...)`

触发时机：

- 子代完成变异后，先正常评估；
- 如果当前问题是 `MaxCoverage`，并且该子代不可行，就进入 repair。

repair 的做法很简单：

- 找出当前子代中取值为 `1` 的位置；
- 从中抽样少量候选位；
- 试探把其中某一位从 `1` 改成 `0`；
- 重新评估这些试探解；
- 选择其中“按可行优先规则最好”的那个；
- 重复这个过程，直到解变可行，或者预算不允许继续修复。

这一步的本质不是“优化”，而是“把明显越界的子代往可行域拉回来”。

### 6. 历史最优解更新逻辑同步修改

文件：

- `main.py`

以前的历史最优更新条件是：

```python
if fitness > population_state.best_y:
```

现在改成：

- 先计算当前子代的 `solution_sort_key`
- 再计算当前历史最优的 `solution_sort_key`
- 只有当前子代的 key 更好，才更新历史最优

这样做的意义是：

- 历史最优不会再因为一个不可行但表面 `fitness` 更高的解而被覆盖；
- `best_x` 的语义变得更一致，和 survival 的规则保持统一。

## 本次修改的设计思路

### 1. 不再继续依赖单一惩罚权重

前面已经试过直接把选择逻辑写成类似：

```text
fitness - violation * w
```

这个方向的问题是：

- 权重很难稳定；
- `violation` 在当前 IOH 接口里的含义并不完全等同于“超预算量”；
- 一个固定权重容易误伤本来不错的解。

所以这一版改成了更稳的词典序思路：

1. 先判断可行性；
2. 再判断质量。

### 2. 保持黑箱风格

当前 IOH 的 Python 接口没有直接暴露显式的成本数组或预算参数。  
因此这次修改没有尝试去“解析真实 cost”，而是完全依赖黑箱接口：

- `problem(x)`
- `problem.constraints.violation()`
- `problem.constraints.penalty()`

这保证了代码仍然符合当前项目的黑箱设定。

### 3. 只对 `MaxCoverage` 生效，尽量不影响 `MaxCut`

这一轮修改是有针对性的，并不是想把整个框架都改掉。  
因此判断入口统一写成：

- 如果是 `MaxCoverage`，启用 `prefer_feasible`
- 如果不是 `MaxCoverage`，保持原逻辑

这样 `MaxCut` 仍然基本不受影响。

### 4. repair 设计成轻量级，而不是重型局部搜索

repair 的目标不是“把每个子代都修到最好”，而是：

- 尽量低成本；
- 尽量少吃预算；
- 只在不可行时介入。

所以我没有在这一版里加入复杂的一删一加局部搜索，也没有做完整贪心修复，而是只做了一个短路径、采样式的删除修复。

## 当前观察到的效果

这一版在小预算测试里表现是变好的。

快速验证结果包括：

- `main.py --problem-id 2100 --budget 200 --runs 1 --pop-size 20 --seed 0`
  - `best=405.0`
  - `final_mean=321.833`
- `make smoke-maxcoverage` 已经能够完整跑通，并生成：
  - `results/report_plots/maxcoverage_curves_v6.png`

此外，单独抽查 repair 的行为时，可以看到：

- 一个明显不可行的解在 repair 前：
  - `fitness=-10.0`
  - `violation=20.0`
  - `penalty=-10.0`
- repair 后变成：
  - `fitness=286.0`
  - `violation=10.0`
  - `penalty=0.0`

这说明 repair 至少完成了它最基本的目标：  
把明显不可行的子代拉回可行区间。

## 这一版没有改动的部分

为了控制变量，这一版没有改下面这些内容：

- 锦标赛父代选择仍然沿用现有逻辑；
- 交叉方式仍然是 `uniform_crossover`；
- 变异方式仍然是标准 bitwise mutation；
- 初始化仍然是随机初始化，没有再加贪心初始化。

也就是说，这一轮主要改变的是：

- `survival`
- `best solution update`
- `child repair`

## 后续可继续尝试的方向

如果这一版在正式实验里继续稳定有效，下一步最值得继续试的方向有两个：

### 1. repair 后再加一个很短的一删一加局部搜索

思路是：

- 先把 child 修成可行；
- 再尝试做 1 到 2 步小范围交换；
- 只接受正增益变化。

### 2. 把父代选择也切换到更一致的可行优先规则

当前这一版已经把 survival 和历史最优改成了 `feasible-first`，  
但父代锦标赛还没有完全同步到同一规则。  
如果后面需要进一步统一搜索压力，可以考虑把 parent selection 也一起调整。

## 小结

这一版修改的核心不是“大幅换算法”，而是把 `MaxCoverage` 的约束信息真正接进当前框架，让算法在保留、修复和记录最优解时都能意识到“可行性”。

一句话概括就是：

> 从“只看 fitness 的单目标保留”改成“可行优先的保留 + 对不可行子代进行轻量修复”。
