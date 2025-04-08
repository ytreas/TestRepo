var paymentForm = $('#payment_form');
var submitBtn = $('#submit_btn');
submitBtn.on('click', function (e) {
    e.preventDefault();
    var method = $(":input[name='payment_method']:checked").val();
    if (method == 'esewa') {
        var tam = $('#tAmt').val();
        var amt = $('#amt').val();
        var txAmt = $('#txAmt').val();
        var psc = $('#psc').val();
        var pdc = $('#pdc').val();
        var scd = $('#scd').val();
        var fu = $('#fu').val();
        var su = $('#su').val();
        var pid = $('#pid').val();
        var url = "https://uat.esewa.com.np/epay/main";
        const baseUrl = window.location.origin
        const success_url = baseUrl+'/payment-success';
        const failure_url = baseUrl+'payment-failure';
        const d = {
            amt: amt,
            psc: 0,
            pdc: 0,
            txAmt: 0,
            tAmt: tam,
            pid: pid,
            scd: "EPAYTEST",
            su: success_url,
            fu: failure_url,
        }

        var form = document.createElement("form");
        form.setAttribute("method", "POST");
        form.setAttribute("action", url);

        for (var key in d) {
            var hiddenField = document.createElement("input");
            hiddenField.setAttribute("type", "hidden");
            hiddenField.setAttribute("name", key);
            hiddenField.setAttribute("value", d[key]);
            form.appendChild(hiddenField);
        }
        document.body.appendChild(form);
        form.submit();
    }
    if(method=='khalti'){
        location.href="/khalti-initiate";
    }

})


