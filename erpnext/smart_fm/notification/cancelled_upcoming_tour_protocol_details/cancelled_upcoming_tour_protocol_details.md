<div>
    <style>
        .container {
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .header {
            background-color: #f4f4f4;
            padding: 10px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
        }
        .content {
            padding: 10px;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }
    </style>
    <div class="container">
        <div class="header">
            Upcoming Tour Protocol Checklist
        </div>
        <div class="content">
            <p>Hello All,</p>
            <p>I hope you’re doing well. Please take note that the below tour has been cancelled:</p>
            <ul>
                <li><strong>Group Name:</strong> {{ doc.group_name }}</li>
                <li><strong>Date:</strong> {{ doc.date }}</li>
                <li><strong>Time:</strong> {{ doc.start_time }} - {{ doc.end_time }} </li>
                <li><strong>No. of Participants:</strong> {{ doc.participants }}</li>
                <li><strong>Contact No.:</strong> {{ doc.contact_no }}</li>
                <li><strong>Email:</strong> {{ doc.email }}</li>
                <li><strong>Tour IC:</strong> {{ doc.tour_ic }}</li>
                <li><strong>Digital Team IC:</strong> {{ doc.digital_team_ic }}</li>
                <li><strong>VIP Status:</strong> {{ doc.vip_status }}</li>
                <li><strong>Tour Route:</strong> {{ doc.tour_type }}</li>
                <li>
                    <strong>Packages of Vegetables to Prepare:</strong> 
                    {%- for item in doc.vegetable -%}
                        {{ item.vegetable }} x{{ item.qty }},
		            {%- endfor -%}
                </li>
            </ul>
            <p>Thank you.</p>
        </div>
        <div class="footer">
            This is an automated message, please do not reply.
        </div>
    </div>
    {{frappe.render_template("templates/end_support.html", {})}}
</div>