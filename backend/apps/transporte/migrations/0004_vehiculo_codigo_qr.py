# Generated manually for Transporte QR persistence

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transporte', '0003_agendalogistica_residencialwfm_wfmjob'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiculo',
            name='codigo_qr',
            field=models.FileField(
                blank=True,
                help_text='Ruta del archivo PNG del código QR generado.',
                max_length=255,
                null=True,
                upload_to='transporte/codigos-qr/',
            ),
        ),
    ]
