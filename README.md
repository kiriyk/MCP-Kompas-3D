# kompas-local-mcp

Минимальный локальный MCP stdio для КОМПАС-3D v21, Windows и Python 3.12+. Реальные вызовы API5/API7 выполняются последовательно в одном COM STA потоке. Протокол обслуживается асинхронно. HTTP, база данных и произвольное выполнение Python не нужны.

## Установка и запуск

Из каталога проекта в PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
$env:KOMPAS_EXECUTABLE = 'D:\ASCON\KOMPAS-3D v21\Bin\KOMPAS.exe'
.venv\Scripts\python.exe -m kompas_local_mcp.server
```

Укажите фактический путь своей установки. SDK с `lib/kAPI5.tlb` и `lib/kAPI7.tlb` должен находиться рядом с Bin; иначе задайте `KOMPAS_SDK`. КОМПАС предпочтительно открыть самостоятельно до подключения: диалоги запуска могут блокировать COM. `connect(launch=true)` умеет запускать его при отсутствии в ROT. Сервер ожидает MCP JSON-RPC на stdin; stdout используется только для протокола, диагностика — stderr.

Пример настройки MCP-клиента (абсолютный путь к Python обязателен):

```json
{
  "mcpServers": {
    "kompas-local": {
      "command": "C:/Users/user/DevProjects/MCP-Kompas-3D/.venv/Scripts/python.exe",
      "args": ["-m", "kompas_local_mcp.server"],
      "env": {
        "KOMPAS_EXECUTABLE": "D:/ASCON/KOMPAS-3D v21/Bin/KOMPAS.exe"
      }
    }
  }
}
```

Формат секции зависит от клиента. Проект пока не добавлен в глобальную конфигурацию Codex; проверка использует настоящий stdio-клиент из examples/client.py.

## 38 инструментов

| Группа | Инструменты |
| --- | --- |
| Подключение и документы | connect, create_drawing, open_document, close_document, save_document, document_state |
| Лист, виды и слои | set_sheet, create_view, set_active_view, view_to_sheet, create_layer, set_active_layer |
| Геометрия и оформление | line, rectangle, circle, arc, text, linear_dimension, hatch_rectangle |
| Сложная геометрия | polyline, mixed_contour, bezier, hatch_polygon |
| Симметрия и массивы | mirror_object, linear_array, circular_array |
| Работа с объектами | copy_object, move_object, move_objects, resize_rectangle, edit_text, rotate_object, delete_object, list_objects |
| Выделение и перенос | get_selected_objects, copy_objects_to_document |
| Экспорт | export_png, export_pdf |

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
