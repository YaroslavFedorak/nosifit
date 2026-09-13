export function enableDragAndDrop(
    card: HTMLElement,
    index: number,
    onMove: (fromIndex: number, toIndex: number) => void
): void {
    card.draggable = true;

    card.addEventListener("dragstart", event => {
        const dragEvent = event as DragEvent;

        if (!dragEvent.dataTransfer) {
            return;
        }

        dragEvent.dataTransfer.effectAllowed = "move";
        dragEvent.dataTransfer.setData(
            "text/plain",
            String(index)
        );

        card.classList.add(
            "db-plan-card-dragging"
        );
    });

    card.addEventListener("dragend", () => {
        card.classList.remove(
            "db-plan-card-dragging"
        );

        card.classList.remove(
            "db-plan-card-drag-over"
        );
    });

    card.addEventListener("dragover", event => {
        event.preventDefault();

        const dragEvent = event as DragEvent;

        if (dragEvent.dataTransfer) {
            dragEvent.dataTransfer.dropEffect =
                "move";
        }

        card.classList.add(
            "db-plan-card-drag-over"
        );
    });

    card.addEventListener("dragleave", () => {
        card.classList.remove(
            "db-plan-card-drag-over"
        );
    });

    card.addEventListener("drop", event => {
        event.preventDefault();

        card.classList.remove(
            "db-plan-card-drag-over"
        );

        const dragEvent = event as DragEvent;

        if (!dragEvent.dataTransfer) {
            return;
        }

        const fromIndex = Number(
            dragEvent.dataTransfer.getData(
                "text/plain"
            )
        );

        if (
            !Number.isInteger(fromIndex) ||
            fromIndex === index
        ) {
            return;
        }

        onMove(fromIndex, index);
    });
}