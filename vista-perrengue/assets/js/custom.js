/* ---------------------------------------------------------------- */
/* Personalizações do template por @meu.perrengue                   */
/* ---------------------------------------------------------------- */

// assets/js/custom.js
document.addEventListener("DOMContentLoaded", function() {
  const openBtns = document.querySelectorAll(".open-info");
  const overlay = document.getElementById("custom-overlay");
  const modal = document.getElementById("custom-modal");
  const modalBody = document.getElementById("custom-modal-body");
  const closeBtnSelector = ".custom-modal-close";

  function openCustomModal(htmlContent) {
    // Injetar o conteúdo
    modalBody.innerHTML = "";
    modalBody.appendChild(htmlContent);

    // Mostrar
    overlay.classList.add("active");
    modal.classList.add("active");
    document.documentElement.classList.add("is-custom-modal-open"); // para possíveis estilos
    // bloquear scroll principal
    document.body.style.overflow = "hidden";
    // acessibilidade
    modal.setAttribute("aria-hidden", "false");
    overlay.setAttribute("aria-hidden", "false");
  }

  function closeCustomModal() {
    overlay.classList.remove("active");
    modal.classList.remove("active");
    document.documentElement.classList.remove("is-custom-modal-open");
    document.body.style.overflow = ""; // restaurar
    modal.setAttribute("aria-hidden", "true");
    overlay.setAttribute("aria-hidden", "true");
    // limpar conteúdo (opcional)
    setTimeout(() => { modalBody.innerHTML = ""; }, 200);
  }

  // abrir ao clicar nos links .open-info
  openBtns.forEach(btn => {
    btn.addEventListener("click", function(e) {
      e.preventDefault();
      const id = this.dataset.info; // ex: "prod1"
      if (!id) return;
      const source = document.getElementById(`info-${id}`);
      if (!source) return;
      // clonar conteúdo para não remover do DOM original
      const clone = source.cloneNode(true);
      // se o clone tem style display:none, removemos para mostrar
      clone.style.display = "";
      // abrir modal com o clone
      openCustomModal(clone);
    });
  });

  // fechar ao clicar no overlay
  overlay.addEventListener("click", function(e) {
    closeCustomModal();
  });

  // fechar ao clicar no botão X (delegation)
  document.addEventListener("click", function(e) {
    if (e.target.matches(closeBtnSelector) || e.target.closest(closeBtnSelector)) {
      closeCustomModal();
    }
  });

  // fechar esc
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape" || e.key === "Esc") {
      if (modal.classList.contains("active")) closeCustomModal();
    }
  });
});

// ============================================================
// Formulário "Get in touch" -> abrir e-mail com campos preenchidos
// ============================================================

document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("contact-form");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault(); // impede o envio padrão do formulário

    // Captura os valores digitados
    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const message = document.getElementById("message").value.trim();

    // Monta o link mailto:
    const destinatario = "canalmeuperrengue@gmail.com"; // <-- altere para o seu e-mail real
    const assunto = encodeURIComponent(`Mensagem de ${name || "visitante"} via @VistaPerrengue`);
    const corpo = encodeURIComponent(
      `Nome: ${name}\nE-mail: ${email}\n\nMensagem:\n${message}`
    );

    // Cria o link e abre o cliente de e-mail
    const mailtoLink = `mailto:${destinatario}?subject=${assunto}&body=${corpo}`;
    window.location.href = mailtoLink;
  });
});
