document.addEventListener('DOMContentLoaded', () => {
  // Toggle password visibility
  document.querySelectorAll('.toggle[data-target]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.target;
      const input = document.getElementById(id);
      if (!input) return;
      input.type = input.type === 'password' ? 'text' : 'password';
      btn.textContent = input.type === 'password' ? 'Показати' : 'Приховати';
    });
  });

  // Simple client-side password confirmation check
  const registerForm = document.querySelector('form[action$="send_verification"], form[action$="verify/send_code"]');
  if (registerForm) {
    registerForm.addEventListener('submit', (e) => {
      const p1 = registerForm.querySelector('input[name="password"]');
      const p2 = registerForm.querySelector('input[name="confirm_password"]');
      if (p1 && p2 && p1.value !== p2.value) {
        e.preventDefault();
        showInlineError(p2, 'Паролі не співпадають');
      }
    });
  }

  function showInlineError(input, message) {
    let el = input.parentElement.querySelector('.inline-error');
    if (!el) {
      el = document.createElement('div');
      el.className = 'inline-error';
      el.style.color = 'var(--danger)';
      el.style.fontSize = '13px';
      el.style.marginTop = '6px';
      input.parentElement.appendChild(el);
    }
    el.textContent = message;
    input.focus();
  }

  // Focus first input
  const firstInput = document.querySelector('.auth-form .form-input');
  if (firstInput) firstInput.focus();
});
