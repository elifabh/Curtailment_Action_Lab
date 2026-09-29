"""Predict from a trusted local joblib model and the documented feature schema.

Usage: python predict.py sample_request.json
Never deserialize joblib files from untrusted sources.
"""
from pathlib import Path
import sys,json
import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
bundle=joblib.load(ROOT/'total_dispatch_down_model.joblib')
request=json.loads(Path(sys.argv[1]).read_text())
assert request['feature_names']==bundle['feature_names'],'Feature order differs'
x=pd.DataFrame([row['features'] for row in request['intervals']],columns=bundle['feature_names'])
assert np.isfinite(x.to_numpy()).all(),'Non-finite inputs are not allowed'
forecast=np.maximum(0,bundle['model'].predict(x))
out={'issue_utc':request['issue_utc'],'model':'local-weather-HGB',
 'microsoft_AI_connected':False,
 'intervals':[{'target_utc':row['target_utc'],'forecast_dispatch_down_MW':float(p)}
  for row,p in zip(request['intervals'],forecast)]}
print(json.dumps(out))
