# Каталог kompas-local-mcp v0.5.0

Снимок 41 публичной сигнатуры из Adapter. При отличии актуальные tools/list и исходники важнее. Параметры self исключены; вызывай MCP именованными JSON-аргументами. Все document_id/reference получаются в текущей сессии. Размеры и координаты — мм вида, если не оговорено иначе. Методы обычно возвращают dict; не выдумывай ключи результата, читай ответ.

## connect

```python
connect(executable: str | None = None, launch: bool = False) -> dict
```

Connect to KOMPAS v21 using installed SDK. Set KOMPAS_EXECUTABLE or pass executable.

## create_drawing

```python
create_drawing() -> dict
```

Create a separate visible drawing, never reuse the active user document.

## open_document

```python
open_document(path: str) -> dict
```

Open or reuse a saved drawing and issue fresh session references.

## close_document

```python
close_document(document_id: str) -> dict
```

Close a registered document WITHOUT saving. Save explicitly first.

## save_document

```python
save_document(document_id: str, path: str) -> dict
```

Save with a normalized absolute Windows path and verify file/path postconditions.

## set_sheet

```python
set_sheet(document_id: str, format: Literal['A0', 'A1', 'A2', 'A3', 'A4'] = 'A0', landscape: bool = True) -> dict
```

Set standard sheet format and verify actual dimensions (Update may return false).

## document_state

```python
document_state(document_id: str) -> dict
```

Read actual sheet and view settings, not cached request arguments.

## create_view

```python
create_view(document_id: str, name: str, scale: float = 1, x: float = 0, y: float = 0, angle: float = 0) -> dict
```

Create and activate a view. Model coordinates are mm; scale is 0.02 for 1:50; angle in degrees.

## set_active_view

```python
set_active_view(document_id: str, view_number: int) -> dict
```

Activate a view through API7 and verify the current number.

## view_to_sheet

```python
view_to_sheet(document_id: str, view_number: int, x: float, y: float) -> dict
```

Convert owner-view coordinates to sheet mm, including rotation and scale.

## create_layer

```python
create_layer(document_id: str, name: str, number: int, color: int = 0) -> dict
```

Create and activate a layer in the current view. Color is Windows COLORREF.

## set_active_layer

```python
set_active_layer(document_id: str, number: int) -> dict
```

Activate an existing layer in the current view.

## line

```python
line(document_id: str, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> dict
```

Draw a finite line segment in the active view (mm).

## rectangle

```python
rectangle(document_id: str, x: float, y: float, width: float, height: float, angle: float = 0, style: int = 1) -> dict
```

Draw a rectangle, angle in degrees, dimensions in real mm.

## circle

```python
circle(document_id: str, x: float, y: float, radius: float, style: int = 1) -> dict
```

Draw a circle in real mm.

## arc

```python
arc(document_id: str, x: float, y: float, radius: float, start_angle: float, end_angle: float, style: int = 1) -> dict
```

Draw a counterclockwise arc with degree angles, e.g. a door swing.

## text

```python
text(document_id: str, x: float, y: float, value: str, height: float = 3.5, angle: float = 0, font: str = 'Arial') -> dict
```

Create native text. Height is paper text height in mm; x/y are model coordinates.

## linear_dimension

```python
linear_dimension(document_id: str, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, orientation: Literal['horizontal', 'vertical', 'parallel'] = 'horizontal') -> dict
```

Create a native linear dimension, not separate lines/text.

## hatch_rectangle

```python
hatch_rectangle(document_id: str, x: float, y: float, width: float, height: float, step: float = 100, angle: float = 45) -> dict
```

Native rectangular hatch. Boundary in owner mm, hatch step in paper mm; angle degrees.

## copy_object

```python
copy_object(document_id: str, reference: str, dx: float, dy: float) -> dict
```

Copy a session-scoped object by a translation in owner mm.

## move_object

```python
move_object(document_id: str, reference: str, dx: float, dy: float) -> dict
```

Move an object by owner mm; stale or cross-document references are rejected.

## rotate_object

```python
rotate_object(document_id: str, reference: str, x: float, y: float, angle: float) -> dict
```

Rotate an object around owner x/y by angle in degrees.

## delete_object

```python
delete_object(document_id: str, reference: str) -> dict
```

Delete a session-scoped object and invalidate its token.

## list_objects

```python
list_objects(document_id: str, coordinate_space: Literal['owner', 'sheet'] = 'owner', limit: int = 5000) -> dict
```

List supported native 2D objects with fresh references; point coordinates respect the requested space.

## export_png

```python
export_png(document_id: str, path: str, dpi: int = 100, color_mode: Literal['black', 'layer'] = 'black') -> dict
```

Export the native full drawing sheet to PNG; no screen capture fallback.

## polyline

```python
polyline(document_id: str, points: list[list[float]], closed: bool = False, style: int = 1) -> dict
```

Create one native polyline from owner-mm vertices.

## mixed_contour

```python
mixed_contour(document_id: str, segments: list[dict], style: int = 1) -> dict
```

One native contour containing lines and circular arcs, in owner mm/degrees.

## bezier

```python
bezier(document_id: str, nodes: list[dict], closed: bool = False, style: int = 1) -> dict
```

Native Bezier nodes: x,y,angle,left,right; handle lengths in owner mm.

## mirror_object

```python
mirror_object(document_id: str, reference: str, x1: float, y1: float, x2: float, y2: float, copy: bool = True) -> dict
```

Mirror about an owner-space axis. copy=False replaces the source and invalidates its handles.

## linear_array

```python
linear_array(document_id: str, reference: str, count: int, dx: float, dy: float) -> dict
```

Native copies along a line; count includes the unchanged original. Not an associative array.

## circular_array

```python
circular_array(document_id: str, reference: str, count: int, x: float, y: float, sweep: float = 360) -> dict
```

Native copies about owner x/y; count includes source. Full circle excludes duplicate endpoint.

## hatch_polygon

```python
hatch_polygon(document_id: str, points: list[list[float]], step: float = 3.5, angle: float = 45) -> dict
```

Native hatch of a simple polygon; step is paper mm, vertices owner mm.

## export_pdf

```python
export_pdf(document_id: str, path: str, paper: Literal['sheet', 'A0', 'A1', 'A2', 'A3', 'A4'] = 'sheet', landscape: bool = True, color: bool = True) -> dict
```

Export a saved, unchanged single-sheet CDW via KOMPAS Pdf2d.dll. Fit paper without changing the drawing format.

## get_selected_objects

```python
get_selected_objects(document_id: str) -> dict
```

Read native selection in a registered drawing; return supported objects with session references.

## copy_objects_to_document

```python
copy_objects_to_document(source_id: str, target_id: str, references: list[str] | None = None, selected: bool = False, dx: float = 0, dy: float = 0) -> dict
```

Copy explicit or selected native objects between registered documents, in target active-view model coordinates. Source is retained.

## resize_rectangle

```python
resize_rectangle(document_id: str, reference: str, width: float, height: float) -> dict
```

Change an existing rectangle in place; retain its origin, angle, layer and reference.

## edit_text

```python
edit_text(document_id: str, reference: str, value: str) -> dict
```

Replace native text in place, keeping position and font. Use nonempty single-line text.

## move_objects

```python
move_objects(document_id: str, references: list[str], dx: float, dy: float) -> dict
```

Move a room/module: walls, hatches, equipment, labels and dimensions together in one view. No persistent grouping.

## set_object_properties

```python
set_object_properties(document_id: str, reference: str, angle: float | None = None, style: int | None = None) -> dict
```

Set absolute angle for a rectangle and/or standard line style 1..9 for geometric primitives. Text, contours, Beziers, hatches and dimensions are excluded. Retains origin/reference; rollback on failure.

## edit_linear_dimension

```python
edit_linear_dimension(document_id: str, reference: str, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, orientation: Optional[Literal['horizontal', 'vertical', 'parallel']] = None) -> dict
```

Update existing native linear dimension endpoints and offset in owner-mm. Orientation None retains it. KOMPAS may reposition text along the dimension line. Does not resize geometry.

## get_object_boundaries

```python
get_object_boundaries(document_id: str, reference: str) -> dict
```

Read native contour or hatch boundaries and exact union bounds in owner-mm (no stroke width). Supports lines and circular arcs; rejects other segment types. No CAD mutation.

## Правила параметров и границы

- polyline: points — [[x,y],...], 2..1000, closed=True требует ≥3; соседние вершины не повторять. Стиль задавай именованно.
- mixed_contour: 1..1000 segments. Отрезок: {"type":"line","x1":0,"y1":0,"x2":100,"y2":0}; дуга: {"type":"arc","x":100,"y":100,"radius":100,"start_angle":270,"end_angle":360}. Дуги CCW. Агент отвечает за стыковку и замкнутость; это один нативный контур.
- bezier: 2..500 nodes: {"x":0,"y":0,"angle":0,"left":0,"right":100}; left/right — неотрицательные длины управляющих плеч, angle — градусы. Пропущенные поля становятся нулями, поэтому задавай узлы явно.
- linear_array/circular_array: целый count 2..500, включает исходник. Линейный dx/dy не оба ноль. sweep ненулевой, |sweep|≤360. При полном круге шаг sweep/count, при неполном sweep/(count-1). Ответ copies содержит только новые копии; total_count включает исходник.
- hatch_polygon: простой многоугольник ≥3 вершин; step — мм бумаги. Не рассчитывай на автоматическую обработку самопересечений. hatch_rectangle имеет default step=100, поэтому для обычной штриховки явно задавай, например, step=3.5.
- create_view: scale — коэффициент, не знаменатель. x/y — положение на листе, angle — поворот вида. set_active_view требует номер из фактического ответа/состояния.
- create_layer: number и color проверяй в исходниках/схеме; color — нативное целое цветовое значение КОМПАС, не строка hex. Перед созданием цветных маршрутов активируй нужный слой и проверяй PNG(color_mode="layer").
- list_objects: limit 5000 default, максимум 10000; проверяй truncated. owner/sheet не смешивать при вычислении переносов.
- rotate_object: угол относительный; set_object_properties(angle=...) абсолютный и только для rectangle. resize_rectangle меняет ширину/высоту, а не позицию.
- Сохранение/экспорт/перенос и ограничения редактирования: editing-and-verification.md. Токены/тайм-ауты/пакеты: local-workflow.md.
