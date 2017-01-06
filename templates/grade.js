function quiz(answers) {

    // first, hide the submit button
    var sub = document.getElementById("submit-quiz");
    sub.style.visibility = "hidden";

    var form = document.getElementById("quiz");
    var len = answers.length;

    var q = [];

    // For each question, check whether the user got the right answer
    for (var i = 1; i <= len; i++) {
        q = document.getElementsByName("q-" + i);

        for (var j = 0; j < q.length; j++) {
            if (q[j].value == answers[i-1]) {
                q[j].parentNode.style.background = "#92a8d1"; // BLUE-ish
            }
            else if (q[j].checked == true) {
                q[j].parentNode.style.backgroundColor = "#f7cac9";  // RED-ish
            }
        }
    }

    return false;
}
