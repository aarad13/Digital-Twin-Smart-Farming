import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

TARGET = 'Volumetric_Moisture_Pct'
AR_COLS = ['moisture_now','lag_1h','lag_6h','lag_24h','lag_72h','mean_prev_1h','mean_prev_6h','std_prev_6h','Hour_sin','Hour_cos','Day_sin','Day_cos']
ENV_COLS = AR_COLS + ['Atm_Temperature_C','Atm_Pressure_inHg','Soil_Temperature_C','Sensor_Board_Temperature_C']

def build_features(df):
    parts=[]
    for farm,g in df.groupby('Farm_ID', sort=True):
        g=g.sort_values('Timestamp').copy()
        y=g[TARGET]
        X=pd.DataFrame(index=g.index)
        X['moisture_now']=y
        for k,n in [(4,'lag_1h'),(24,'lag_6h'),(96,'lag_24h'),(288,'lag_72h')]:
            X[n]=y.shift(k)
        X['mean_prev_1h']=y.rolling(4,min_periods=4).mean()
        X['mean_prev_6h']=y.rolling(24,min_periods=24).mean()
        X['std_prev_6h']=y.rolling(24,min_periods=24).std()
        for c in ['Hour_sin','Hour_cos','Day_sin','Day_cos','Atm_Temperature_C','Atm_Pressure_inHg','Soil_Temperature_C','Sensor_Board_Temperature_C']:
            X[c]=g[c]
        for h in [1,6]:
            X[f'target_{h}h']=y.shift(-4*h)
        d=pd.concat([g[['Timestamp']],X],axis=1).dropna().reset_index(drop=True)
        d['Farm_ID']=farm
        parts.append(d)
    return pd.concat(parts,ignore_index=True)

def metric_row(split,farm,fold,h,features,model,train_n,test_n,y,pred):
    return dict(split=split,farm=farm,fold=fold,horizon_h=h,features=features,model=model,
                train_n=train_n,test_n=test_n,MAE=mean_absolute_error(y,pred),
                RMSE=np.sqrt(mean_squared_error(y,pred)),R2=r2_score(y,pred))

def main():
    ap=argparse.ArgumentParser(description='Purged chronological evaluation for predictive soil-moisture models.')
    ap.add_argument('--data',default='kolkata_unified_dataset.csv')
    ap.add_argument('--output-dir',default='.')
    args=ap.parse_args()
    data=Path(args.data); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(data,parse_dates=['Timestamp']).sort_values(['Farm_ID','Timestamp']).reset_index(drop=True)
    required=['Timestamp','Farm_ID',TARGET,'Hour_sin','Hour_cos','Day_sin','Day_cos',
              'Atm_Temperature_C','Atm_Pressure_inHg','Soil_Temperature_C','Sensor_Board_Temperature_C']
    missing=[x for x in required if x not in df.columns]
    if missing: raise ValueError(f'Missing required columns: {missing}')
    if df[required].isna().any().any(): raise ValueError('Missing values found in required columns; inspect before modelling.')
    farms=list(df['Farm_ID'].drop_duplicates())
    if len(farms)!=2: raise ValueError(f'Expected two farm IDs, found {farms}')
    for farm,g in df.groupby('Farm_ID'):
        diffs=g.sort_values('Timestamp')['Timestamp'].diff().dropna()
        if not (diffs == pd.Timedelta(minutes=15)).all():
            raise ValueError(f'Non-uniform 15-minute intervals in {farm}')
    features=build_features(df)
    model_specs={
        'Ridge': lambda: make_pipeline(StandardScaler(),Ridge(alpha=1.0)),
        'Random Forest': lambda: RandomForestRegressor(n_estimators=35,max_depth=12,min_samples_leaf=5,max_features=0.9,n_jobs=-1,random_state=42)
    }
    rows=[]
    for farm,g in features.groupby('Farm_ID',sort=True):
        g=g.sort_values('Timestamp').reset_index(drop=True)
        n=len(g); boundaries=[(int(.50*n),int(.65*n)),(int(.65*n),int(.80*n)),(int(.80*n),n)]
        for h in [1,6]:
            target_col=f'target_{h}h'; purge=4*h
            for fold,(a,b) in enumerate(boundaries,1):
                train_end=max(0,a-purge)
                tr=g.iloc[:train_end]; te=g.iloc[a:b]
                y=te[target_col].to_numpy()
                pred=te['moisture_now'].to_numpy()
                rows.append(metric_row('within-farm-expanding-purged',farm,fold,h,'persistence','Persistence',len(tr),len(te),y,pred))
                for fset,cols in [('autoregressive',AR_COLS),('environment_augmented',ENV_COLS)]:
                    for name,maker in model_specs.items():
                        model=maker(); model.fit(tr[cols],tr[target_col]); pr=model.predict(te[cols])
                        rows.append(metric_row('within-farm-expanding-purged',farm,fold,h,fset,name,len(tr),len(te),y,pr))
    # Directional held-out-farm transfer. The test farm contributes its own recent moisture history;
    # this is not a cold-start transfer. Both farms share calendar dates and regional conditions.
    for trf,tef in [(farms[0],farms[1]),(farms[1],farms[0])]:
        tr=features[features.Farm_ID==trf]; te=features[features.Farm_ID==tef]
        for h in [1,6]:
            target_col=f'target_{h}h'; y=te[target_col].to_numpy(); pred=te['moisture_now'].to_numpy()
            rows.append(metric_row('directional-held-out-farm',f'{trf}->{tef}',1,h,'persistence','Persistence',len(tr),len(te),y,pred))
            for fset,cols in [('autoregressive',AR_COLS),('environment_augmented',ENV_COLS)]:
                for name,maker in model_specs.items():
                    model=maker(); model.fit(tr[cols],tr[target_col]); pr=model.predict(te[cols])
                    rows.append(metric_row('directional-held-out-farm',f'{trf}->{tef}',1,h,fset,name,len(tr),len(te),y,pr))
    res=pd.DataFrame(rows)
    summary=res.groupby(['split','horizon_h','features','model']).agg(
        evaluations=('MAE','size'),MAE=('MAE','mean'),MAE_sd=('MAE','std'),
        RMSE=('RMSE','mean'),RMSE_sd=('RMSE','std'),R2=('R2','mean'),R2_sd=('R2','std'),
        total_test_n=('test_n','sum')).reset_index()
    res.to_csv(out/'research_experiment_all_folds.csv',index=False)
    summary.to_csv(out/'research_experiment_summary.csv',index=False)
    print('scikit-learn',sklearn.__version__,'data_rows',len(df),'feature_rows',len(features),'evaluations',len(res))
    print(summary.to_string(index=False,float_format=lambda x:f'{x:.4f}'))

if __name__=='__main__': main()
