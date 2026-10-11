# Расширение MCP: сначала прямой API, затем stdio

Проект src/kompas_local_mcp: adapter.py (базовый API), features.py (сложная геометрия), edits.py (редактирование), advanced_edits.py (свойства/размеры/границы), io_features.py (экспорт/перенос), worker.py (STA), core.py (проверки). server.py публикует методы Adapter через FastMCP; актуальный список получай tools/list. Не добавляй произвольный execute_python_script в публичный MCP для обхода отсутствующего метода.

Порядок: прочитай реализацию и официальный SDK; сформулируй результат; проверь прямым коротким скриптом на отдельном документе; проверь фактические свойства/геометрию и Save/Close/Open; добавь валидируемый Adapter-метод; проверь stdio-вызов и ошибки; обнови README, docs/verification.md, соответствующие probes и этот скилл. Не изменяй рабочий пользовательский чертёж ради эксперимента. Не выполняй прямой COM параллельно MCP. Прямой скрипт нужен для изоляции COM от протокола и исследования API, а не для подмены результата инструмента.

SDK относительно каталога установки: `SDK/lib/kAPI5.tlb`, `SDK/lib/kAPI7.tlb`, `SDK/Include/KsTLB.pas` и `SDK/Include/ksAPI7.pas`. Определи путь из KOMPAS_EXECUTABLE/KOMPAS_SDK локальной конфигурации. Используй generated typelib и явный QueryInterface для нужного интерфейса; не угадывай члены по COM GetTypeInfo. Все обращения к COM — на одном STA потоке. Проверяй конечность чисел, диапазоны, принадлежность reference документу/виду, поддержанные типы и откат частичного создания. Нативные операции могут вернуть успех без применения свойства, либо ложь после успешного применения: требуй чтение результата.

Известные особенности v21:

- ksOpenView иногда возвращает 0 при фактическом переключении; после Update проверяй API7 Current.
- Format.Update может вернуть False после применения; сверяй LayoutSheet/Format.
- LayerNumber setter не применял слой; рабочий путь — ksChangeObjectLayer после Update.
- DrawingContours — имя коллекции, не Contours. Сегменты требуют IContourLineSegment/IContourArc; центр дочерней дуги — Xc/Yc.
- IContour.Style setter не применял стиль: текущий публичный set_object_properties это запрещает.
- Шрифт текста подтверждай сохранением/переоткрытием: временно восстановленный ITextFont не доказывает стойкость.
- SaveAs и обновления требуют проверки нового файла/фактических свойств. Нельзя объявлять успех по одному return value.

Примеры проверок: examples/probe_advanced_edits_direct.py и probe_advanced_edits_mcp.py; examples/client.py — JSON-RPC transport. docs/advanced-edits.md и docs/revision-5.md..revision-7.md фиксируют наблюдения. Юнит-тесты не заменяют живой COM, а живой COM не заменяет проверку stdio-схем. Отделяй подтверждённое от ограничений. Проверено локально на v21 для 2D; не обобщай на 3D/другие версии без испытаний.
