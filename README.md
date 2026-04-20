# LLVM IR Function Aggregation Prototype

Небольшой исследовательский прототип для анализа функций в LLVM IR.
Сейчас проект содержит модульный LLVM-pass, который:

- находит все определённые в модуле функции;
- считает количество IR-инструкций в каждой функции;
- сортирует функции по размеру;
- выводит верхние 20% функций по числу инструкций.

Это можно использовать как базовый шаг для дальнейшей агрегации эвристик
с уровня отдельных функций на уровень единицы трансляции.

## Структура проекта

- `cpp/Top20BiggestFuncs.cpp` - LLVM-pass для анализа функций модуля;
- `cpp/main.cpp` - небольшой тестовый пример;
- `cpp/run.sh` - вспомогательный скрипт сборки и запуска pass-плагина;
- `python/compile_gym_bridge.py` - мост между `CompilerGym` и локальным LLVM-pass;
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

## Дальнейшее развитие

Логичное следующее направление для дипломной работы:

- перейти от простого ранжирования функций к агрегации на уровне translation unit;
- встроить pass в контур автонастройки компилятора.
