@app.route('/api/stocks/daily_business_states', methods=['GET'])
def get_daily_business_states():
    try:
        conn = get_sql_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT id, product_name, quantity, unit_id, price_per_unit, customer_name, amount, transaction_type, entry_datetime, entry_by
            FROM business
        """
        cursor.execute(query)
        business_data = cursor.fetchall()
        fetch_unit_name = "SELECT unit_name FROM unit_of_measure WHERE id = %s"
        for item in business_data:
            cursor.execute(fetch_unit_name, (item['unit_id'],))
            unit_name_result = cursor.fetchone()
            item['unit_name'] = unit_name_result['unit_name'] if unit_name_result else None
        cursor.close()
        return jsonify(business_data)
    except Error as e:
        return jsonify({'error': str(e)}), 500