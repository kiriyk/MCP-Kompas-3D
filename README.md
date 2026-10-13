# kompas-local-mcp

Локальный MCP stdio для КОМПАС-3D v21, Windows и Python 3.12+. Реальные вызовы API5/API7 выполняются последовательно в одном COM STA потоке. Протокол обслуживается асинхронно. HTTP, база данных и произвольное выполнение Python не нужны.

## Установка и запуск

Из каталога проекта в PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
$env:KOMPAS_EXECUTABLE = 'C:\path\to\KOMPAS-3D v21\Bin\KOMPAS.exe'
.venv\Scripts\python.exe -m kompas_local_mcp.server
```

Укажите фактический путь своей установки. SDK с `lib/kAPI5.tlb` и `lib/kAPI7.tlb` должен находиться рядом с Bin; иначе задайте `KOMPAS_SDK`. КОМПАС предпочтительно открыть самостоятельно до подключения: диалоги запуска могут блокировать COM. `connect(launch=true)` умеет запускать его при отсутствии в ROT. Сервер ожидает MCP JSON-RPC на stdin; stdout используется только для протокола, диагностика — stderr.

Пример настройки MCP-клиента (абсолютный путь к Python обязателен):

```json
{
  "mcpServers": {
    "kompas_3d": {
      "command": "C:/path/to/MCP-Kompas-3D/.venv/Scripts/python.exe",
      "args": ["-m", "kompas_local_mcp.server"],
      "env": {
        "KOMPAS_EXECUTABLE": "C:/path/to/KOMPAS-3D v21/Bin/KOMPAS.exe"
      }
    }
  }
}
```

Формат секции зависит от клиента. Для Codex см. [config/codex.example.toml](config/codex.example.toml): перенесите секцию в пользовательский config.toml и замените условные пути. Команда `codex mcp get kompas_3d` проверяет регистрацию. После изменения конфигурации обновите подключение или перезапустите Codex. Не публикуйте заполненную локальную конфигурацию.

Пример регистрации из PowerShell после установки пакета (замените пути):

```powershell
codex mcp add kompas_3d --env 'KOMPAS_EXECUTABLE=C:/path/to/KOMPAS-3D v21/Bin/KOMPAS.exe' --env 'PYTHONIOENCODING=utf-8' -- 'C:/path/to/MCP-Kompas-3D/.venv/Scripts/python.exe' -m kompas_local_mcp.server
```

Переменные среды: KOMPAS_EXECUTABLE — установленный EXE, KOMPAS_SDK — отдельный SDK при нестандартной структуре, KOMPAS_MCP_CACHE — необязательный каталог COM wrappers (по умолчанию временная папка ОС). Сервер не содержит путей к конкретной машине.

## 71 инструмент (v0.7)

| Группа | Инструменты |
| --- | --- |
| Подключение и документы | connect, create_drawing, open_document, close_document, save_document, document_state |
| Лист, виды и слои | set_sheet, create_view, set_active_view, view_to_sheet, create_layer, set_active_layer |
| Геометрия и оформление | line, rectangle, circle, arc, text, linear_dimension, hatch_rectangle |
| Сложная геометрия | polyline, mixed_contour, bezier, hatch_polygon |
| Симметрия и массивы | mirror_object, linear_array, circular_array |
| Работа с объектами | copy_object, move_object, move_objects, resize_rectangle, edit_text, rotate_object, delete_object, list_objects, set_object_properties, edit_linear_dimension, get_object_boundaries |
| Выделение и перенос | get_selected_objects, copy_objects_to_document |
| Экспорт | export_png, export_pdf |
| 3D документы | create_part, create_assembly, open_model, save_model, close_model, model_state, rebuild_model |
| 3D операции | create_sketch, sketch_polygon, sketch_circle, extrude, set_extrusion_depth, set_model_color, set_model_material |
| Сборки и STL | insert_component, set_component_placement, list_components, export_model |
| Виды по модели | create_model_view, create_section_view, model_view_state, update_model_views |

Сначала connect → create_drawing/open_document → использовать возвращенный document_id во всех операциях. Ссылки reference действуют только в текущем процессе сервера и своем документе. После закрытия документа или удаления объекта все его ссылки недействительны. close_document закрывает без сохранения: сначала явно вызовите save_document.

Координаты и габариты геометрии — миллиметры своего вида. Scale — коэффициент, 1:50 = 0.02. Углы — градусы. Начало вида задается в миллиметрах листа. Высота текста и шаг штриховки задаются в миллиметрах бумаги. list_objects поддерживает координаты owner и sheet, view_to_sheet учитывает поворот и масштаб. Линейные размеры — нативные объекты КОМПАСа; таблица в демонстрации составлена из линий и текста.

При тайм-ауте 60 секунд исход операции неизвестен: она может продолжать выполняться в КОМПАСе. Автоматического повтора нет; проверьте состояние. Занятый worker отклоняет следующий вызов. Отмена MCP-запроса не отменяет выполняющийся COM-вызов. Сервер не закрывает КОМПАС при завершении процесса.

## Пример и проверки

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe examples/probe.py
.venv\Scripts\python.exe examples/build_factory.py
.venv\Scripts\python.exe examples/probe_direct.py
.venv\Scripts\python.exe examples/build_factory_direct.py
.venv\Scripts\python.exe examples/probe_features_mcp.py
.venv\Scripts\python.exe examples/probe_io_direct.py
.venv\Scripts\python.exe examples/probe_io_mcp.py
.venv\Scripts\python.exe examples/build_factory_v4_direct.py
```

Для live-примеров требуется KOMPAS_EXECUTABLE и открытый КОМПАС. probe создаёт свой тестовый документ, сохраняет, экспортирует, закрывает и повторно открывает. build_factory создаёт учебный план 40×24 м на А0 горизонтальном, 1:50: два производственных помещения, кухня, раздевалка, склады, проезд 4 м и пешеходный проход 1.5 м. Результаты в artifacts/. Повторный запуск заменяет файлы примеров.

Вторая редакция: build_factory_direct.py чертит напрямую через API, без протокола. Сначала функции проверены в probe_direct.py, затем добавлены в MCP и проверены в probe_features_mcp.py. [Описание редакции 2](docs/revision-2.md) содержит источники технологии, изменения плана и новые особенности API. export_png(color_mode="layer") сохраняет цвета слоёв. count в массивах включает оригинал; круговой массив поворачивает копии вместе с положением вокруг центра. Это обычные нативные копии, без ассоциативной связи массива.

См. [результаты и особенности API](docs/verification.md), [проектирование](docs/design.md). Исходники подготовлены для GitHub; виртуальное окружение, кэш COM, чертежи и журналы исключены из Git. Публикация не выполнялась.

MCP основан на [официальном Python SDK](https://github.com/modelcontextprotocol/python-sdk). Сигнатуры и константы CAD проверены по локальному SDK v21; справка ASCON для [штриховки API5](https://help.ascon.ru/KOMPAS_SDK/22/ru-RU/ksdocument2d_kshatch.html) использована как дополнительный источник.

## Нативный PDF, тексты и перенос

`export_pdf` вызывает установленный `Bin/Pdf2d.dll` через API КОМПАСа. Никакого внешнего генератора PDF нет. Перед экспортом вызовите `save_document`: грязный или несохранённый документ отклоняется, чтобы не выгрузить старую версию с диска. Пока поддержан один лист.

- `paper="sheet"`: размер исходного листа, масштаб 1.
- `paper="A4"` (также A0–A3), `landscape=true`: весь исходный лист вписывается в заданную бумагу. Формат CDW сохраняется.
- `color=true`: цвета слоёв; `color=false`: чёрно-белые линии. Параметры конвертера восстанавливаются после вызова. Файл публикуется только после проверки свежего результата и сигнатуры `%PDF-`.

`text(..., font="Arial")` по умолчанию использует Arial. Проверены кириллица, —, →, × и Ø. В GOST type A некоторые Unicode-символы показываются квадратами или неверными буквами. Требуются Update текстового элемента **и** всего объекта. У `arc` направление против часовой стрелки: API7 Direction=false, 0→90 создаёт четверть окружности.

`copy_objects_to_document(source_id, target_id, references=[...], dx=0, dy=0)` копирует нативную геометрию в активный вид целевого чертежа. Координаты в миллиметрах вида: разный масштаб источника и назначения не меняет реальные габариты. Вместо references можно `selected=true`: выделите объекты в исходном документе. `get_selected_objects` возвращает эти объекты и ссылки. Поддерживаются типы из list_objects; другие типы отклоняются до копирования. Исходник сохраняется, системный буфер обмена не используется. При ошибке до вставки временная группа очищается; при неопределённом результате после вставки выдаются оставшиеся API references для проверки перед повтором.

[Актуальная редакция 4 и особенности API](docs/revision-3.md): охлаждающий тоннель сохранён, широкий центральный коридор убран; склады заполнены стеллажами с проездами. Добавлены корректные дверные дуги, native PDF и перенос.

[Актуальная редакция 5](docs/revision-5.md): 40 шкафчиков, две линии, загруженные паллеты и фасад стеллажа. Проверены редактирование и перенос комнат; добавлены resize_rectangle, edit_text и move_objects.

[Редакция 6](docs/revision-6.md): две цепочки подготовки массы, обновлённые кухонные столы и стулья, отдельные входы WC/душевой, двери всех туалетных кабинок и раковины у стен.

[Редакция 7](docs/revision-7.md): исправлены наклоны мебели, сантехники и стен, оставшиеся старые зеркальные стулья удалены.

[Дополнительные операции v0.5](docs/advanced-edits.md): set_object_properties (абсолютный угол и стиль), edit_linear_dimension (существующий размер), get_object_boundaries (границы контуров и штриховок).

## Скилл для агента

[skills/kompas-mcp-workflow/SKILL.md](skills/kompas-mcp-workflow/SKILL.md) описывает работу агента с зарегистрированным stdio MCP: 80 методов, сессии и ссылки, виды и масштабы, составные правки, нативные размеры, сохранение и PDF, тайм-ауты и расширение через SDK. Скилл использует зарегистрированные инструменты; отдельного клиента или обхода отсутствующего подключения в нём нет.

Для установки скопируйте папку skills/kompas-mcp-workflow в каталог пользовательских скиллов Codex, например `$HOME/.agents/skills/kompas-mcp-workflow`. Если среда использует `$CODEX_HOME/skills`, установите туда, не создавая дубликат. Метаданные agents/openai.yaml объявляют зависимость от MCP с именем kompas_3d; при другом имени регистрации согласуйте её. Регистрация сервера — отдельная локальная настройка. При обновлении синхронизируйте источник с установленной копией и проверяйте актуальные tools/list.


## 3D учебный сценарий: Dice Tower

Соглашения координат, вызовы, ограничения: [3D workflow](skills/kompas-mcp-workflow/references/model-workflow.md). Сервер v0.6 добавляет 22 команды: детали, сборки, эскизы, выдавливания/вырезы, изменение глубины, цвет, материал, положения компонентов, STL и нативные связанные виды/разрезы.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe examples\probe_models_mcp.py --output C:\path\to\verification
.venv\Scripts\python.exe examples\build_dice_tower.py --output C:\path\to\tower
.venv\Scripts\python.exe examples\build_dice_tower_drawings.py --output C:\path\to\tower
```

Башня: 220 мм, корпус 90×90, три перегородки 35°, лоток, выходной скат, съёмная задняя стенка, портал и стилизованные силуэты Рика/Морти. 8 разных деталей, 10 компонентов, 9 CDW/PDF листов. JSON рядом содержит параметры, состояние и протокол вызовов. Проверяется проход для кубика 22 мм по диагонали с запасом, но динамика падения и печатные посадки требуют физического испытания. Сборка использует внешние ссылки: перемещайте всю папку и переукажите пути при необходимости. Ниже исторические проверки 2D остаются применимы.

После обновления перезапустите подключение MCP: tools/list должен возвращать 80 команд. Прямой цветной PNG модели проверен; STEP пока не объявлен проверенным. Это рабочее покрытие учебного сценария, а не весь SDK.

## Сложные формы (v0.7)

Опубликованы `sketch_arc`, `loft` (base/boss/cut), `sweep` (base), `shell`, `fillet`, `list_model_topology`, `set_model_display`, `export_model_png`. Ссылки топологии привязаны к документу и истекают при rebuild. Селектор перечисляет только грани/рёбра тел; вспомогательная геометрия не входит. `model_state` проверяет новые формообразующие операции.

Через свежий stdio проверены полый loft и sweep, fillet с откатом недопустимого радиуса, shell внутрь/наружу, сохранение/закрытие/повторное открытие и цветной PNG. Историческая проверка v0.7: 27 tests passed. Учебная V2: 19 деталей, 36 компонентов, 20 ассоциативных чертежей. Это компоновка для обучения API; крепления и физический ход кубика требуют прототипа. Сценарии V2.1 принимают пути через CLI.

## Контроль геометрии и сборки v0.8

Добавлены девять публичных инструментов: семантический выбор топологии; нативные расстояния и проверки выбранных пар; пересечения сборки с разделением контактов и объёмного наложения; выбор результирующих тел; цвет документа/тела/грани/компонента; повторяемая камера; upsert и удаление вхождений. Всего 80 инструментов. Проверка толщины ограничена выбранными гранями, динамика кубика не моделируется.

```powershell
.venv\Scripts\python.exe examples\probe_inspection_mcp.py --output C:\path\to\verification --executable "D:\ASCON\KOMPAS-3D v21\Bin\KOMPAS.exe"
.venv\Scripts\python.exe examples\build_dice_tower_v2.py --output C:\path\to\tower
.venv\Scripts\python.exe examples\build_dice_tower_v2_drawings.py --output C:\path\to\tower
```

V2.1: 27 разных деталей и 42 вхождения. Скаты установлены на интегральных полках, выходной скат имеет две опоры, трубы — посадочные бобышки и кольца, задняя сервисная крышка — четыре отверстия под M3. Передние рельефы имеют отдельные глаза, зрачки, бровь, нос, зубы и одежду. Это стилизованные нативные рельефы, не точная скульптура референса. Клеевые контакты и винтовая крышка требуют проверки допусков и сборки на физическом прототипе.

Новый запуск сохраняется в runs/run-*; current.json публикуется только после нативной проверки и отсутствия объёмных коллизий. Повтор использует SHA256 проверенных файлов и не добавляет дубликаты. Старые ревизии сохраняются. Чертежи содержат ассоциативные виды всех деталей и сборки. Не запускайте несколько клиентов COM одновременно. После обновления сервера перезапустите MCP-соединение клиента.

Сохранение уже связанного источника в тот же путь использует Save без промежуточного переименования; проверяются свежесть файла, Changed и PathName. При тайм-ауте сначала прочитайте состояние.
