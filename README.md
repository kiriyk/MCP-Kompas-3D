# MCP-Kompas-3D

**Локальный MCP-сервер для КОМПАС-3D v21: нативные 2D-чертежи, 3D-детали и сборки, ассоциативные виды и проверки геометрии.**

Текущая версия — **v0.8.0, 80 инструментов**. Сервер работает на Windows с Python 3.12+ через stdio и SDK API5/API7. Вызовы COM выполняются последовательно в одном STA-потоке; протокол MCP обслуживается асинхронно.

## Возможности

- Создание и редактирование 2D-геометрии, текстов, размеров, штриховок, слоёв и видов; массивы, зеркалирование и перенос объектов между документами.
- Нативные 3D-эскизы, выдавливания и вырезы, loft по сечениям, sweep по траектории, оболочки и скругления.
- Сборки с файловыми ссылками и проверяемым размещением компонентов; вставка, upsert без дубликатов и удаление вхождений.
- Выбор граней и рёбер по геометрическим условиям, нативные расстояния между выбранными объектами и проверка пересечений компонентов.
- Цвет и прозрачность документа, тела, грани и компонента; материал, плотность и повторяемые ориентации камеры.
- Ассоциативные виды и разрезы модели на чертеже; сохранение M3D/A3D/CDW, нативный PDF и PNG, экспорт STL.
- Два скилла для агента и воспроизводимые учебные сценарии, включая разноцветную Dice Tower V2.1.

Это проверенное покрытие части SDK v21. Проверки расстояний относятся к выбранным граням/рёбрам; автоматическая проверка минимальной толщины всего тела и динамическая симуляция кубиков не реализованы. STEP не объявлен проверенным.

## Установка

Требуются Windows, установленный КОМПАС-3D v21 с SDK и Python 3.12+.

```powershell
git clone git@github.com:kiriyk/MCP-Kompas-3D.git
cd MCP-Kompas-3D
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
$env:KOMPAS_EXECUTABLE = 'C:\path\to\KOMPAS-3D v21\Bin\KOMPAS.exe'
.venv\Scripts\python.exe -m kompas_local_mcp.server
```

Замените путь на свою установку. SDK с `lib/kAPI5.tlb` и `lib/kAPI7.tlb` ожидается рядом с `Bin`; при другой структуре задайте `KOMPAS_SDK`. `KOMPAS_MCP_CACHE` задаёт необязательный каталог COM wrappers, по умолчанию используется временная папка ОС.

Сервер ожидает MCP JSON-RPC на stdin. stdout используется только для протокола, stderr — для диагностики. Для работы нужен запущенный КОМПАС; `connect(launch=true)` может запустить его, если он отсутствует в ROT. Диалоги запуска способны задержать COM-вызовы.

## Подключение MCP-клиента

Используйте абсолютный путь к Python виртуального окружения:

```json
{
  "mcpServers": {
    "kompas_3d": {
      "command": "C:/path/to/MCP-Kompas-3D/.venv/Scripts/python.exe",
      "args": ["-m", "kompas_local_mcp.server"],
      "env": {
        "KOMPAS_EXECUTABLE": "C:/path/to/KOMPAS-3D v21/Bin/KOMPAS.exe",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

После обновления пакета перезапустите MCP-подключение и проверьте `tools/list`: для v0.8 должно быть 80 инструментов. Настройки с путями конкретного компьютера храните локально.

## Каталог инструментов v0.8

| Группа | Инструменты |
| --- | --- |
| Подключение и 2D-документы | `connect`, `create_drawing`, `open_document`, `close_document`, `save_document`, `document_state` |
| Лист, виды и слои | `set_sheet`, `create_view`, `set_active_view`, `view_to_sheet`, `create_layer`, `set_active_layer` |
| 2D-геометрия и оформление | `line`, `rectangle`, `circle`, `arc`, `text`, `linear_dimension`, `hatch_rectangle`, `polyline`, `mixed_contour`, `bezier`, `hatch_polygon` |
| Симметрия и массивы | `mirror_object`, `linear_array`, `circular_array` |
| Редактирование объектов | `copy_object`, `move_object`, `move_objects`, `resize_rectangle`, `edit_text`, `rotate_object`, `delete_object`, `list_objects`, `set_object_properties`, `edit_linear_dimension`, `get_object_boundaries` |
| Выделение и перенос | `get_selected_objects`, `copy_objects_to_document` |
| 2D-экспорт | `export_png`, `export_pdf` |
| 3D-документы | `create_part`, `create_assembly`, `open_model`, `save_model`, `close_model`, `model_state`, `rebuild_model` |
| 3D-эскизы и операции | `create_sketch`, `sketch_polygon`, `sketch_circle`, `sketch_arc`, `extrude`, `set_extrusion_depth`, `loft`, `sweep`, `shell`, `fillet` |
| Вид и свойства модели | `set_model_color`, `set_model_material`, `set_model_display`, `export_model_png`, `set_model_appearance`, `set_model_orientation`, `list_model_bodies` |
| Геометрические проверки | `list_model_topology`, `select_model_topology`, `measure_model_geometry`, `check_model_measurements`, `check_assembly_intersections` |
| Сборки и STL | `insert_component`, `set_component_placement`, `list_components`, `upsert_component`, `remove_component`, `export_model` |
| Ассоциативные виды | `create_model_view`, `create_section_view`, `model_view_state`, `update_model_views` |

Параметры берите из текущих схем `tools/list`. Общие правила и подробности SDK находятся в [скилле workflow](skills/kompas-mcp-workflow/SKILL.md) и [проверках v0.8](skills/kompas-mcp-workflow/references/inspection-v08.md).

## Учебная Dice Tower V2.1

Сценарий строит изогнутый полый корпус с прозрачным окном, четыре внутренних ската, гнутые трубы, портал, лоток, сервисную крышку и отдельные цветные рельефы Рика и Морти. **27 исходных деталей, 42 компонента и 28 ассоциативных чертежей.**

```powershell
# Офлайн-тесты: КОМПАС не требуется
.venv\Scripts\python.exe -m unittest discover -s tests -v

# Нативная проверка MCP: требуется КОМПАС
.venv\Scripts\python.exe examples\probe_inspection_mcp.py --output artifacts\verification

# Сборка и комплект чертежей
.venv\Scripts\python.exe examples\build_dice_tower_v2.py --output artifacts\dice-tower-v2
.venv\Scripts\python.exe examples\build_dice_tower_v2_drawings.py --output artifacts\dice-tower-v2
```

Укажите `KOMPAS_EXECUTABLE`; примеры также принимают `--executable`. Запускайте COM-сценарии последовательно. Новая сборка создаётся в `runs/run-*`, а `current.json` публикуется после нативной проверки и отсутствия объёмных пересечений. Повтор сверяет SHA256 и переиспользует проверенные файлы без добавления компонентов. Модели, чертежи и локальные журналы не включены в Git: их создают сценарии.

В проверенном экземпляре V2.1 проверена **861 пара компонентов: объёмных пересечений нет**. На выбранных гранях измерены толщина ската 2,5 мм, толщина крышки 3 мм и зазор между соседними скатами не менее 49,46 мм; диаметр портала — 82 мм. Офлайн-набор v0.8 содержит **72 прошедших теста**. Эти результаты описывают проверенный экземпляр, а не гарантируют работоспособность любой изменённой геометрии.

Скаты имеют интегральные опорные полки, трубы — посадочные бобышки и кольца, крышка — отверстия под четыре M3. Допуски печати, прочность, соединения и физическое движение кубика требуют прототипа. Рельефы стилизованы и упрощены относительно концепта. Для переноса A3D/CDW перемещайте всю папку исходных моделей; при необходимости переукажите внешние ссылки.

## Правила работы и ограничения

- Сначала `connect`, затем создайте или откройте документ и используйте возвращённый `document_id`. Ссылки объектов действуют в своей сессии и документе; ссылки топологии истекают при перестроении и изменении размещения.
- Геометрия задаётся в миллиметрах, объём — в мм³, плотность — в г/см³, углы — в градусах. Масштаб вида — коэффициент: 1:50 соответствует `0.02`. Высота текста — миллиметры бумаги.
- `close_document` и `close_model` закрывают без сохранения. Сохраняйте явно и не закрывайте чужие документы ради проверки.
- Тайм-аут 60 секунд означает неизвестный исход. Вызов может продолжаться в КОМПАСе; сначала прочитайте состояние, не повторяйте мутацию автоматически. Не запускайте несколько COM-клиентов одновременно.
- Нативный PDF использует `Bin/Pdf2d.dll`, требует сохранённого чертежа и поддерживает один лист за вызов. PNG использует штатный растровый экспорт, STL не сохраняет цвета.
- COLORREF имеет порядок BBGGRR. `transparency_percent=0` означает непрозрачность; в SDK параметр Transparency имеет обратный смысл. Для собственного цвета используйте проверяемые настройки документа/тела/грани/компонента.
- Проверка пересечений различает контакты и объёмные наложения; расстояния относятся только к выбранным ограниченным объектам. Отсутствие коллизий не доказывает сборочный доступ или динамику.

## Скиллы и документация

- [kompas-mcp-workflow](skills/kompas-mcp-workflow/SKILL.md): подключение, документы, 2D/3D-операции, ссылки, сохранение, экспорт и диагностика.
- [kompas-complex-modeling](skills/kompas-complex-modeling/SKILL.md): сложные формы по референсу, loft/sweep/shell/fillet, разноцветные сборки и проверка геометрии.

Скопируйте нужные папки из `skills/` в каталог пользовательских скиллов вашей среды, например `$CODEX_HOME/skills`. Объявленная зависимость использует имя MCP `kompas_3d`; согласуйте его с регистрацией сервера. При обновлении синхронизируйте установленную копию со скиллом репозитория.

История учебного 2D-проекта и особенности API: [верификация](docs/verification.md), [проектирование](docs/design.md), [редакция 2](docs/revision-2.md), [редакции 3–4](docs/revision-3.md), [редакция 5](docs/revision-5.md), [редакция 6](docs/revision-6.md), [редакция 7](docs/revision-7.md), [операции v0.5](docs/advanced-edits.md). Ранние 2D- и 3D-примеры сохранены в `examples/`.

MCP основан на [официальном Python SDK](https://github.com/modelcontextprotocol/python-sdk). CAD-сигнатуры проверены по установленному SDK КОМПАС-3D v21; дополнительные рецепты и ссылки ASCON приведены в скиллах. Сервер не публикует произвольное выполнение Python.
