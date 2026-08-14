from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, request

from analysis.model_service import predict_dataframe, build_analysis

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")

_last_result = None

@analysis_bp.post("/import-analysis")
def import_analysis():
    global _last_result

    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "message": "请选择Excel或CSV文件"}), 400

    filename = uploaded_file.filename or ""
    file_bytes = uploaded_file.read()

    try:
        if filename.lower().endswith(".csv"):
            try:
                raw_df = pd.read_csv(BytesIO(file_bytes), encoding="utf-8-sig")
            except UnicodeDecodeError:
                raw_df = pd.read_csv(BytesIO(file_bytes), encoding="gbk")
        elif filename.lower().endswith((".xlsx", ".xls")):
            raw_df = pd.read_excel(BytesIO(file_bytes))
        else:
            return jsonify({
                "success": False,
                "message": "仅支持 .csv、.xlsx、.xls 文件"
            }), 400

        result_df = predict_dataframe(raw_df)
        analysis = build_analysis(result_df)
        _last_result = analysis

        return jsonify({
            "success": True,
            "message": f"成功分析 {len(result_df)} 条评论",
            "data": analysis,
        })
    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error),
        }), 500

@analysis_bp.get("/analysis/latest")
def latest_analysis():
    if _last_result is None:
        return jsonify({
            "success": False,
            "message": "暂无分析结果，请先导入数据",
        }), 404

    return jsonify({
        "success": True,
        "data": _last_result,
    })
