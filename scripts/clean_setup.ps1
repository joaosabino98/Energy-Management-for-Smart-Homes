# Run from root project folder

Remove-Item .\scheduler\migrations\0*
Remove-Item *.sqlite3
python manage.py makemigrations
python manage.py migrate
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pass')" | python manage.py shell
python manage.py loaddata default_appliances.json
echo 'exec(open("scripts/load_solar_data.py").read())' | python manage.py shell
# python manage.py runserver