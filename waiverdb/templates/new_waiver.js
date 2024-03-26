const WAIVERS_URL = "{{ url_for('api_v1.waivers_resource') }}";

$(document).ready(function () {
    $("form").on("submit", function(ev) {
        ev.preventDefault();
        const testcaseName = $("#testcase").val();
        $.ajax({
            url: WAIVERS_URL,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                subject_type: $("#subject_type").val(),
                subject_identifier: $("#subject_identifier").val(),
                testcase: testcaseName,
                product_version: $("#product_version").val(),
                comment: $("#comment").val(),
                scenario: $("#scenario").val()
            }),
            success: function (data, status, jqXHR) {
                $("#result-text-error").addClass("d-none");
                $("#result-text-success").removeClass("d-none");
                $("#result-link").attr("href", `${WAIVERS_URL}${data.id}`);
                $("#new-waiver-id").text(data.id);
                $("#waiver-result").removeClass("alert-danger d-none").addClass("alert-success");
            },
            error: function (jqXHR, textStatus) {
                $("#result-text-success").addClass("d-none");
                $("#result-text-error").removeClass("d-none");
                let addition = "";
                if(jqXHR.status === 403) {
                    addition = ` | <a href="{{ url_for('api_v1.permissions_resource', html='1')}}&testcase=${encodeURIComponent(testcaseName)}" target="_blank">See who has permissions to waive ${testcaseName}</a>`;
                }
                $("#error-desc").html(`${jqXHR.responseJSON.message}${addition}`);
                $("#waiver-result").removeClass("alert-success d-none").addClass("alert-danger");
            }
        });
    });
});
