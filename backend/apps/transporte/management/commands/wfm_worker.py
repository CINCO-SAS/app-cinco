"""
wfm_worker — F5-5 · worker CLI/cron de la cola de validación WFM.

Port de `transporte_validacion_wfm_worker.php` (que era CLI-only y
reclamaba UN job con `ClaimNextJob` y procesaba UN chunk
(`chunkDays=1, batch=15`) por pasada; el cron lo volvía a llamar).

Uso:
    python backend/manage.py wfm_worker                 # 1 chunk (legacy)
    python backend/manage.py wfm_worker --hasta-completar
    python backend/manage.py wfm_worker --job <uuid>

Comportamiento:
- Reclama el siguiente job pendiente (o un PROCESANDO huérfano, con la
  precedencia del legacy) y avanza UN chunk por defecto.
- `--hasta-completar`: itera chunks hasta que el job termine o falle
  (útil para cron único en vez de invocaciones repetidas).
- `--job`: procesa un job concreto por `job_uuid` (reclamándolo primero).
- Un error marcaría el job como ERROR (como `FailJob` legacy) y sale con
  código 1 para que el cron/alerta lo señale.
"""
import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.transporte.models import WfmJob
from apps.transporte.services import WfmService


class Command(BaseCommand):
    help = "Procesa la cola de validación WFM (reclama un job y avanza chunks)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--job",
            help="job_uuid concreto a procesar (si no, el siguiente de la cola).",
        )
        parser.add_argument(
            "--worker-id",
            default="",
            help="Identidad del worker para locked_by (default: wfm_worker:<pid>).",
        )
        parser.add_argument(
            "--hasta-completar",
            action="store_true",
            help="Procesa chunks hasta completar o fallar el job (default: 1 chunk).",
        )

    def handle(self, *args, **opts):
        worker_id = opts["worker_id"] or "wfm_worker:%s" % os.getpid()

        if opts["job"]:
            job = WfmService.obtener_job(opts["job"])
            if job is None:
                raise CommandError(WfmService.MSG_JOB_NO_ENCONTRADO)
            job = WfmService.reclamar_job(job.job_uuid, worker_id)
            if job is None:
                raise CommandError(
                    "El job no esta reclamable (lo tiene otro worker o termino)."
                )
        else:
            job = WfmService.reclamar_siguiente(worker_id)
            if job is None:
                self.stdout.write("No hay jobs pendientes para procesar.")
                return

        try:
            job = WfmService.procesar_job(job)
            while opts["hasta_completar"] and job.estado == "PROCESANDO":
                job = WfmService.procesar_job(job)
        except Exception as exc:  # noqa: BLE001 — espejo del FailJob legacy
            WfmService.fallar_job(job, exc)
            raise CommandError("Error procesando job WFM: %s" % exc)

        self.stdout.write(
            json.dumps(
                WfmService.formatear_respuesta(job), ensure_ascii=False
            )
        )
