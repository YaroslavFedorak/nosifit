import type {
    PlanExercise
} from "../../api.js";

type Rerender = () => void;

export function enableDrag(
    card: HTMLDivElement,
    index: number,
    list: PlanExercise[],
    rerender: Rerender
): void {
    card.draggable = true;

    card.addEventListener(
        "dragstart",
        event => {
            const dataTransfer =
                event.dataTransfer;

            if (!dataTransfer) {
                return;
            }

            dataTransfer.setData(
                "index",
                String(index)
            );

            card.classList.add(
                "tr-plan-card-dragging"
            );
        }
    );

    card.addEventListener(
        "dragend",
        () => {
            card.classList.remove(
                "tr-plan-card-dragging"
            );
        }
    );

    card.addEventListener(
        "dragover",
        event => {
            event.preventDefault();

            card.classList.add(
                "tr-plan-card-drag-over"
            );
        }
    );

    card.addEventListener(
        "dragleave",
        () => {
            card.classList.remove(
                "tr-plan-card-drag-over"
            );
        }
    );

    card.addEventListener(
        "drop",
        event => {
            event.preventDefault();

            card.classList.remove(
                "tr-plan-card-drag-over"
            );

            const dataTransfer =
                event.dataTransfer;

            if (!dataTransfer) {
                return;
            }

            const from =
                Number(
                    dataTransfer.getData(
                        "index"
                    )
                );

            const to =
                index;

            if (
                Number.isNaN(from) ||
                Number.isNaN(to)
            ) {
                return;
            }

            if (from === to) {
                return;
            }

            const item =
                list.splice(
                    from,
                    1
                )[0];

            if (!item) {
                return;
            }

            list.splice(
                to,
                0,
                item
            );

            rerender();
        }
    );
}