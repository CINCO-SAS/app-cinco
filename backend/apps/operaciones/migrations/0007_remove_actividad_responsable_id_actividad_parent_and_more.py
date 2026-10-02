# Generated manually with SeparateDatabaseAndState to preserve existing columns and add Foreign Keys safely.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0006_agendatecnicoregistro_agendatrabajo_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='actividad',
                    name='responsable_id',
                ),
                migrations.AddField(
                    model_name='actividad',
                    name='parent',
                    field=models.ForeignKey(
                        blank=True,
                        db_column='parent_id',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='sub_actividades',
                        to='operaciones.actividad',
                    ),
                ),
                migrations.AddField(
                    model_name='actividad',
                    name='responsable',
                    field=models.ForeignKey(
                        db_column='responsable_id',
                        help_text='Usuario / Técnico asignado para ejecutar la actividad',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='actividades_asignadas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name='actividad',
                    name='created_by',
                    field=models.ForeignKey(
                        blank=True,
                        db_column='created_by',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='actividades_creadas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name='actividad',
                    name='deleted_by',
                    field=models.ForeignKey(
                        blank=True,
                        db_column='deleted_by',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='actividades_eliminadas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name='actividad',
                    name='updated_by',
                    field=models.ForeignKey(
                        blank=True,
                        db_column='updated_by',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='actividades_actualizadas',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name='agenda',
                    name='color_hex',
                    field=models.CharField(
                        default='#66bb6a',
                        help_text='Color corporativo visual en el calendario',
                        max_length=7,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE operaciones_actividades 
                        ADD CONSTRAINT fk_operaciones_actividades_responsable 
                        FOREIGN KEY (responsable_id) REFERENCES auth_user(id);

                    ALTER TABLE operaciones_actividades 
                        ADD CONSTRAINT fk_operaciones_actividades_created_by 
                        FOREIGN KEY (created_by) REFERENCES auth_user(id) ON DELETE SET NULL;

                    ALTER TABLE operaciones_actividades 
                        ADD CONSTRAINT fk_operaciones_actividades_updated_by 
                        FOREIGN KEY (updated_by) REFERENCES auth_user(id) ON DELETE SET NULL;

                    ALTER TABLE operaciones_actividades 
                        ADD CONSTRAINT fk_operaciones_actividades_deleted_by 
                        FOREIGN KEY (deleted_by) REFERENCES auth_user(id) ON DELETE SET NULL;
                    """,
                    reverse_sql="""
                    ALTER TABLE operaciones_actividades DROP FOREIGN KEY fk_operaciones_actividades_responsable;
                    ALTER TABLE operaciones_actividades DROP FOREIGN KEY fk_operaciones_actividades_created_by;
                    ALTER TABLE operaciones_actividades DROP FOREIGN KEY fk_operaciones_actividades_updated_by;
                    ALTER TABLE operaciones_actividades DROP FOREIGN KEY fk_operaciones_actividades_deleted_by;
                    """,
                ),
            ],
        ),
    ]
