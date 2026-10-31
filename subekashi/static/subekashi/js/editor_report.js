window.addEventListener('DOMContentLoaded', () => {
    const reasonEle = document.getElementById('reason');
    const submitEle = document.getElementById('report-submit');

    // 報告理由が空白だけの間は送信できないようにする
    function updateSubmitState() {
        submitEle.disabled = reasonEle.value.trim() === '';
    }

    reasonEle.addEventListener('input', updateSubmitState);
    // 送信に失敗して開き直したときや、戻るで入力が残っているときも合わせる
    updateSubmitState();
});
