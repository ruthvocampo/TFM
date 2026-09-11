import argparse
from datetime import datetime

from src.simulator.simulator import Simulator
def main():

    parser = argparse.ArgumentParser(
        description="Simulador logístico Kafka"
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help=(
            "Número de horas simuladas "
            "a ejecutar."
        )
    )

    parser.add_argument(
        "--realtime",
        action="store_true",
        help=(
            "Espera 60 segundos reales "
            "por cada hora simulada."
        )
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Elimina el estado persistido "
            "y crea una simulación nueva."
        )
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # FECHA INICIAL
    # ---------------------------------------------------------
    #
    # Solo se utiliza si NO existe state.json.
    #

    fecha_actual = datetime(
        2026,
        9,
        11,
        6,
        0,
        0
    )

    simulator = Simulator(
        fecha_actual
    )

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------

    if args.reset:

        simulator.reset_state()

    # ---------------------------------------------------------
    # RUN
    # ---------------------------------------------------------

    simulator.run(
        steps=args.steps,
        realtime=args.realtime
    )


if __name__ == "__main__":

    main()