import argparse
from datetime import datetime

from src.simulator.simulator import Simulator


def main():
    parser = argparse.ArgumentParser(
        description="Simulador logístico Kafka"
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=60.0,
        help=(
            "Minutos simulados por segundo real. "
            "60 = 1 minuto simulado por segundo real."
        )
    )

    parser.add_argument(
        "--step-minutes",
        type=int,
        default=1,
        help=(
            "Minutos simulados que avanza el reloj "
            "en cada tick."
        )
    )

    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help=(
            "Cada cuántos ticks se guarda el estado."
        )
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Elimina el estado persistido "
            "y comienza una simulación nueva."
        )
    )

    parser.add_argument(
        "--no-batch",
        action="store_true",
        help=(
            "No genera los archivos batch iniciales."
        )
    )

    args = parser.parse_args()

    # ---------------------------------------------------------
    # FECHA INICIAL
    # ---------------------------------------------------------

    fecha_inicial = datetime(
        2026,
        9,
        17,
        6,
        0
    )

    # ---------------------------------------------------------
    # CREAR SIMULADOR
    # ---------------------------------------------------------

    simulator = Simulator(
        fecha_inicial
    )

    # ---------------------------------------------------------
    # EJECUTAR UN DÍA
    # ---------------------------------------------------------

    simulator.run_day(
        simulated_minutes_per_second=args.speed,
        start_time=fecha_inicial,
        reset=args.reset,
        step_minutes=args.step_minutes,
        checkpoint_every_steps=args.checkpoint_every,
        generate_batch=not args.no_batch
    )


if __name__ == "__main__":
    main()