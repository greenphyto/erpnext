<div>
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f4f4f4;
        }
    </style>
    <p>Dear Farm Manager,</p>
    <p>This is an automated notification for tomorrow’s scheduled farm visits on <strong>{{ date }}</strong>.</p>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Group Name</th>
                <th>Email</th>
                <th>VIP</th>
                <th>Tour IC</th>
            </tr>
        </thead>
        <tbody>
            {% for visit in doc.doc_list %}
            <tr>
                <td>{{ visit.time }}</td>
                <td>{{ visit.group_name }}</td>
                <td>{{ visit.email or "-" }}</td>
                <td>{{ visit.vip_status }}</td>
                <td>{{ visit.tour_ic or "-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <p>Please ensure the farm is prepared accordingly.</p>
    
    {{end_support}}
</div>