# Run from root project folder

Remove-Item .\coordinator\migrations\0*
Remove-Item .\aggregator\migrations\0*
Remove-Item *.sqlite3
Get-ChildItem '*.pyc' -Force -Recurse | Remove-Item -Force
python manage.py makemigrations
python manage.py migrate
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pass')" | python manage.py shell
python manage.py loaddata default_profiles.json sample_house_data.json
echo 'exec(open("scripts/load_solar_data.py").read())' | python manage.py shell
# python manage.py runserver