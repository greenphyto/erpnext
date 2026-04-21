<p>Dear Purchase Manager,</p>

<p>The following stock items have fallen below their minimum (safety stock) levels:</p>

<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th>Item Code</th>
      <th>Safety Stock</th>
      <th>Current Quantity</th>
      <th>Warehouse</th>
    </tr>
  </thead>
  <tbody>
    {% for row in doc.item_list %}
    <tr>
      <td>{{ row.item_code }}</td>
      <td>{{ row.safety_stock }}</td>
      <td>{{ row.actual_qty }}</td>
      <td>{{ row.warehouse }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<p>Please review and consider restocking these items.</p>

