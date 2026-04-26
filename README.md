# LLVM IR Function Aggregation Prototype

Небольшой исследовательский прототип для анализа функций в LLVM IR.
Сейчас проект содержит модульный LLVM-pass, который:

- находит все определённые в модуле функции;
- считает количество IR-инструкций в каждой функции;
- сортирует функции по размеру;
- выводит верхние 20% функций по числу инструкций;
- строит агрегированное представление для всей translation unit.

Это можно использовать как базовый шаг для дальнейшей агрегации эвристик
с уровня отдельных функций на уровень единицы трансляции.

## Структура проекта

- `cpp/Top20BiggestFuncs.cpp` - LLVM-pass для анализа функций модуля;
- `cpp/main.cpp` - небольшой тестовый пример;
- `cpp/run.sh` - вспомогательный скрипт сборки и запуска pass-плагина;
- `python/compile_gym_bridge.py` - мост между `CompilerGym` и локальным LLVM-pass;
- `python/aggregate_tu_score.py` - агрегация function-level score в TU-level score;
- `python/autotune_tu.py` - простой контур автонастройки по TU-метрике;
- `python/setup_compiler_gym_env.sh` - подготовка совместимого `CompilerGym`-окружения;
- `cpp/CMakeLists.txt` - сборка pass-плагина через CMake.

## Требования

Нужны установленные:

- LLVM с `clang`, `clang++`, `opt` и `LLVMConfig.cmake`;
- CMake 3.13+;
- Python 3.10 для `CompilerGym 0.2.5`;
- bash-совместимая оболочка для запуска `run.sh`.

## Быстрый запуск

```bash
cd cpp
chmod +x run.sh
./run.sh main.cpp
```

Для Ubuntu обычно достаточно:

```bash
sudo apt update
sudo apt install clang llvm llvm-dev cmake
```

Скрипт ищет инструменты в `PATH`, затем в типовых Ubuntu-путях вроде
`/usr/lib/llvm-17/bin`, и поддерживает явные overrides:

```bash
LLVM_DIR=/usr/lib/llvm-17/lib/cmake/llvm ./run.sh main.cpp
CLANG=/usr/bin/clang-17 CLANGXX=/usr/bin/clang++-17 OPT=/usr/bin/opt-17 ./run.sh main.cpp
```

## Что делает pass

Pass регистрируется под именем:

```text
top20-biggest-funcs
```

При запуске он печатает:

- число определённых функций в модуле;
- сколько функций попало в верхние 20%;
- суммарное число IR-инструкций в модуле;
- суммарный размер выбранных функций;
- список выбранных функций и их размер.

Дополнительно pass умеет сохранять результат в JSON:

```bash
./run.sh main.cpp --json-out top20.json --fraction 0.20
```

Это упрощает дальнейшую агрегацию на уровне translation unit и интеграцию
с внешним контуром автонастройки.

Теперь JSON содержит не только список выбранных функций, но и блок
`translation_unit_aggregation` с агрегированными метриками уровня TU:

- доля инструкций в доминирующей функции;
- доля инструкций в top-3 и top-5 функциях;
- средний, медианный размер функции и стандартное отклонение;
- показатели концентрации `HHI` и `Gini`;
- веса `selected_weight_percent` для выбранных функций.

Эти веса можно использовать как метод переноса function-level сигналов
на уровень всей единицы трансляции.

## Интеграция с CompilerGym

Подготовлен базовый мост `python/compile_gym_bridge.py`, который:

- открывает LLVM-окружение `CompilerGym`;
- загружает benchmark;
- при необходимости применяет последовательность действий;
- извлекает текущее bitcode-состояние;
- запускает на нём локальный pass и возвращает JSON-результат.

Пример:

```bash
python3 python/compile_gym_bridge.py \
  --benchmark cbench-v1/qsort \
  --actions 0,12,5 \
  --output result.json
```

Для этого нужен установленный пакет:

```bash
pip install compiler_gym
```

На Ubuntu 24 системный `Python 3.12` для `CompilerGym 0.2.5` не подходит:
нужен отдельный `Python 3.10` environment. Для проекта добавлен setup-скрипт:

```bash
chmod +x python/setup_compiler_gym_env.sh
./python/setup_compiler_gym_env.sh
./.miniforge/envs/cgym-py310/bin/python python/compile_gym_bridge.py \
  --benchmark cbench-v1/qsort \
  --output result.json
```

Если нужно пройти шаги вручную, рабочая последовательность такая:

```bash
bash /tmp/Miniforge3.sh -b -p ./.miniforge
./.miniforge/bin/mamba create -y -n cgym-py310 python=3.10 pip
./.miniforge/bin/mamba install -y -n cgym-py310 "pip<24" "setuptools<66" "wheel<0.39" "numpy<2"
./.miniforge/envs/cgym-py310/bin/pip install compiler_gym
curl -L https://conda.anaconda.org/biobuilds/linux-64/ncurses-5.9-701.tar.bz2 -o /tmp/ncurses-5.9-701.tar.bz2
mkdir -p /tmp/ncurses-5.9-701
tar -xjf /tmp/ncurses-5.9-701.tar.bz2 -C /tmp/ncurses-5.9-701
cp /tmp/ncurses-5.9-701/lib/libncurses.so.5 ./.miniforge/envs/cgym-py310/lib/libtinfo.so.5
./.miniforge/envs/cgym-py310/bin/python python/compile_gym_bridge.py \
  --benchmark cbench-v1/qsort \
  --output result.json
```

Скрипт `compile_gym_bridge.py` сам:

- создаёт локальные каталоги `.compiler_gym/cache`, `.compiler_gym/site_data`,
  `.compiler_gym/transient`;
- складывает туда runtime и benchmark-данные `CompilerGym`;
- подготавливает `LD_LIBRARY_PATH` для старого `compiler_gym-llvm-service`.

## Агрегация на TU

Следующий шаг дипломной работы теперь реализован в базовом виде:
из размера выбранных функций формируются веса, по которым можно агрегировать
любые function-level оценки в один TU-level score.

Пример входного файла со значениями функций:

```json
{
  "function_scores": [
    { "name": "qsortx", "score": 0.9 },
    { "name": "main1", "score": 0.4 }
  ]
}
```

Агрегация:

```bash
python3 python/aggregate_tu_score.py \
  --weights-json python/result.json \
  --scores-json function_scores.json \
  --output tu_score.json
```

Скрипт возьмёт `selected_weight_percent` из JSON pass-а и вычислит
взвешенный TU-level score.

## Автонастройка по TU-метрике

Добавлен базовый autotuning-контур `python/autotune_tu.py`.
Он:

- сэмплирует последовательности оптимизаций в `CompilerGym`;
- применяет их к benchmark;
- запускает наш LLVM pass на полученном bitcode;
- ранжирует последовательности по выбранной TU-метрике.

Пример:

```bash
./.miniforge/envs/cgym-py310/bin/python python/autotune_tu.py \
  --benchmark cbench-v1/qsort \
  --trials 8 \
  --steps 6 \
  --objective top_3_share_percent \
  --output autotune_qsort.json
```

Можно оптимизировать, например:

- `selected_ir_share_percent`
- `dominant_function_share_percent`
- `top_3_share_percent`
- `top_5_share_percent`
- `size_concentration_hhi`
- `size_gini`

## Экспериментальная серия

Для следующего этапа добавлен воспроизводимый сценарий серии экспериментов:
`python/run_experimental_series.py`.

Он запускает для набора benchmark'ов:

- baseline без оптимизационных действий;
- несколько случайных последовательностей pass-действий;
- анализ каждого состояния нашим LLVM-pass;
- сбор TU-level метрик в `series.json`, `summary.csv` и `rankings.json`.

Минимальный smoke-run:

```bash
./.miniforge/envs/cgym-py310/bin/python python/run_experimental_series.py \
  --benchmarks cbench-v1/qsort \
  --trials 2 \
  --steps 3
```

Пилотная серия:

```bash
./.miniforge/envs/cgym-py310/bin/python python/run_experimental_series.py \
  --benchmarks cbench-v1/qsort,cbench-v1/dijkstra,cbench-v1/stringsearch,cbench-v1/rijndael \
  --trials 4 \
  --steps 6 \
  --seed 7
```

Результаты сохраняются в:

```text
experiments/runs/<timestamp>/
```

Для генерации краткого Markdown-отчёта:

```bash
./.miniforge/envs/cgym-py310/bin/python python/summarize_experiment.py \
  experiments/runs/<timestamp>/series.json \
  --output experiments/runs/<timestamp>/report.md
```

## Дальнейшее развитие

Логичное следующее направление для дипломной работы:

- перейти от случайного поиска к более осмысленной стратегии выбора pass-последовательностей;
- сравнить поведение стандартных reward `CompilerGym` и TU-level метрик агрегации;
- оформить экспериментальную методику и набор метрик для главы диплома.
