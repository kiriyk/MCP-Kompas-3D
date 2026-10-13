# Проверка на КОМПАС-3D v21

Проверено 10 октября 2026 на установленном v21. Все инструменты вызываются через MCP stdio, COM выполняется в STA. Поддержка других версий не заявлена.

- Первоначальные 7 unit tests: координаты повернутого вида; пути Windows с Unicode; невалидные числа; документные ссылки; удаление всех алиасов; свежий вывод вместо старого файла; исполнение и исключения одного worker.
- Live probe: 34 MCP-вызова. Проверены А0, масштаб 0.02, поворот 90°, переключение видов, слой 5 у всех примитивов, кириллица, нативные размеры 500/1000, штриховка, copy/move/rotate/delete, отказ невалидных аргументов и удалённого алиаса, PNG, CDW, закрытие и повторное открытие.
- План: 270 объектов, 8 нативных размеров (1500, 4000, 8000, 8000, 11000, 13000, 24000, 40000). Проверены ненулевые слои геометрии, А0 1189×841 мм и вид 1:50. PNG просмотрен визуально. Подробные результаты находятся в artifacts/probe-results.json и factory-verification.json.
- Независимая проверка кода нашла проблемы свежести файлов, алиасов удалённых объектов и блокировки MCP event loop; все три исправлены. COM отменить принудительно безопасным способом пока нельзя.

## Практические нюансы

1. API5 GetTypeInfo на этой установке не работает как ожидается. Используем официальные type libraries и явно типизированные wrappers, без угадывания свойств по позднему binding.
2. API5 ksOpenView может вернуть 0 при успешном переключении. Проверяем фактический Current в API7; перед чтением после установки Current вызываем Update.
3. Format.Update может вернуть false, хотя формат применён. Проверяем реальные Format и VerticalOrientation, а также сохранение после повторного открытия.
4. Для слоя API7 используется LayerNumber. Его setter не обеспечил смену слоя; после Update вызываем API5 ksChangeObjectLayer и проверяем результат.
5. LineDimensions доступна через ISymbols2DContainer. Orientation: horizontal=1, vertical=2, parallel=0. NominalValue читается через IDimensionText.
6. Штриховка: ksHatch, граничные линии, ksEndObj. Вложенный ksContour здесь не нужен. Шаг 3.5 мм бумаги работает; шаг 350 не дал видимой штриховки тонких стен в масштабе 1:50.
7. PNG: параметры из document.RasterFormatParam, не GetParamStruct(96). Проверяем свежий файл с сигнатурой PNG через уникальный временный путь и замену конечного файла.
8. CDW: API7 SaveAs не дает полезного результата. Сначала сохраняем уникальную свежую копию, затем конечный файл; проверяем путь, размер и изменение времени конечного файла. КОМПАС держит открытый файл заблокированным; копия удаляется после переключения документа на конечный путь. При неудаче завершающего сохранения оставляем копию для восстановления. Сравнение CDW побайтно неверно: имя сохранения меняет внутреннее содержимое.
9. Размеры геометрии относятся к виду. Координаты листа вычисляются с переносом, поворотом и масштабом, размеры и радиусы масштабируются отдельно.
10. Разработка и демонстрация относятся к 2D. 3D, DXF, нативные таблицы, привязки и редактирование существующих размеров не включены без проверки. Учебный план не проходил проектную/нормативную экспертизу.

## Проверки v0.3

17 unit tests проходят. После проверки напрямую через SDK: IO MCP probe — 17 вызовов, features MCP probe — 19, базовый live probe — 34. Проверены нативные PDF А1/А4 в цвете/ч/б, Arial, CCW дуга 90°, native selected transfer и смещение между видами разных масштабов. Свежий файл проверяется перед публикацией; формат CDW после PDF не меняется. См. [подробности и актуальный план](revision-3.md).

## Проверки редактирования v0.4

22 unit tests; direct room edit/save/reopen; 11 stdio вызовов редактирования. Фабрика v5 изменена из существующего CDW; 40 шкафчиков, 2 тоннеля и 2 флоупака подтверждены после сохранения и открытия. См. [редакцию 5](revision-5.md).

## Проверки v0.5

28 unit tests; прямой SDK probe трёх новых методов с Save/Close/Open; stdio probe проверяет 41 инструмент, изменения свойств/размеров, границы и отказы некорректным действиям. Подробности в [advanced-edits.md](advanced-edits.md).


### Native color/opacity regression (2026-10-11)

`IColorParam7.Transparency` is opacity in the SDK: 1 is opaque, 0 is invisible.
This is the inverse of the transparency percentage shown in the KOMPAS UI.
The previous `set_model_color` passed 0 and did not check `ksPart.Update`.
Use API7 TopPart, query IColorParam7 explicitly, call SetAdvancedColor with 1,
require TopPart.Update success, then read color and opacity from TopPart again.
Never validate only the transient API5 proxy. Own colors on bodies/faces can
override the top part, and assembly components may inherit their source color.

Validation: 50 unit tests passed (including opacity and failed-update regressions).
Fresh stdio MCP set_model_color/save/close followed by independent native reopen
retained color 0x33FF6B and SDK opacity 1. All 10 saved assembly components were
opaque after reopen. Native COLOR_OBJECT raster export showed colored surfaces.
Generated part files were repaired with backups; volumes remained unchanged.
OpenGL rendering settings require a complete KOMPAS restart to take effect;
reopening a document alone is insufficient.

Sources:
- https://help.ascon.ru/KOMPAS_SDK/22/ru-RU/icolorparam7_transparency.html
- https://help.ascon.ru/KOMPAS/21/ru-RU/28_4_5_osobennosti.html
