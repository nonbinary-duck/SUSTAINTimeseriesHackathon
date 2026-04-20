from flask import Flask, jsonify, render_template, request
import xgboost as xgb
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split

app = Flask(__name__)

# This route "/" is the default page, this will run when the browerser runs the URL
@app.route("/")
def index():
    return render_template("index.html")

# This is called by a acript in the index.html
@app.route("/run")
def run_model():

    # Read the seed from the query string e.g. /run?seed=42, default to 42 if not provided
    seed = int(request.args.get("seed", 42))

    #Makes our test dataset
    X, y = make_regression(n_samples=200, n_features=5, noise=20, random_state=seed)
    #split into test and train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed)

    #Create, fit and run out model
    model = xgb.XGBRegressor(n_estimators=100, max_depth=4, random_state=seed)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    # results /  actuals
    results = [
        {"index": i, "actual": round(float(y_test[i]), 2), "predicted": round(float(preds[i]), 2)}
        for i in range(min(50, len(y_test)))
    ]
    #feature importance results
    importances = [
        {"feature": f"Feature {i}", "importance": round(float(v), 4)}
        for i, v in enumerate(model.feature_importances_)
    ]
    #return these results to script in index.html
    return jsonify({"results": results, "importances": importances})

# Start the server if this file is run directly (python app.py)
if __name__ == "__main__":
    # host="0.0.0.0":
    # listen on all network interfaces without it Flask only listens inside the container 
    # and your browser can't reach it.
    app.run(host="0.0.0.0", port=5001, debug=True)
