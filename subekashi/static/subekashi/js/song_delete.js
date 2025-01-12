// TODO checkValidityを利用
document.getElementById('reason').addEventListener('input', () => {
    reasonValue = document.getElementById("reason").value;
    deleteEle = document.getElementById("deletesubmit");
    deleteEle.disabled = reasonValue == "";
})