# Installation
git clone
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
cd web; npm install; npm run build
python run_devlensx.py api
python run_devlensx.py web

