(function () {
    "use strict";

    const formatRupiah = (angka) => Number(angka).toLocaleString("id-ID");

    // ---- Toast notifikasi -------------------------------------------------
    function tutupToast(toast) {
        toast.classList.add("toast-hide");
        toast.addEventListener("animationend", () => toast.remove(), { once: true });
    }

    document.querySelectorAll(".toast").forEach((toast, index) => {
        toast.querySelector(".toast-close").addEventListener("click", () => tutupToast(toast));
        setTimeout(() => tutupToast(toast), 4500 + index * 500);
    });

    // ---- Tombol kembali ke halaman sebelumnya ------------------------------
    // Pakai riwayat browser jika halaman sebelumnya masih dari aplikasi ini,
    // jika tidak, gunakan href sebagai fallback.
    document.querySelectorAll("[data-back]").forEach((tombol) => {
        tombol.addEventListener("click", (event) => {
            const referrer = document.referrer;
            if (!referrer || referrer === location.href) return;
            if (new URL(referrer).origin !== location.origin) return;
            if (new URL(referrer).pathname === location.pathname) return;

            event.preventDefault();
            history.back();
        });
    });

    // ---- Lihat / sembunyikan password -------------------------------------
    document.querySelectorAll("[data-toggle-password]").forEach((tombol) => {
        const input = document.getElementById(tombol.dataset.togglePassword);
        tombol.addEventListener("click", () => {
            const tersembunyi = input.type === "password";
            input.type = tersembunyi ? "text" : "password";
            tombol.textContent = tersembunyi ? "Sembunyikan" : "Lihat";
        });
    });

    // ---- Progress bar (lebar diatur lewat JS karena CSP melarang inline style)
    document.querySelectorAll("[data-width]").forEach((bar) => {
        requestAnimationFrame(() => {
            bar.style.width = bar.dataset.width + "%";
        });
    });

    // ---- Dialog konfirmasi hapus ------------------------------------------
    function tampilkanKonfirmasi(pesan) {
        return new Promise((resolve) => {
            const overlay = document.createElement("div");
            overlay.className = "modal-overlay";
            overlay.innerHTML = `
                <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
                    <h3 id="modal-title">Konfirmasi</h3>
                    <p class="modal-message"></p>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-ghost" data-batal>Batal</button>
                        <button type="button" class="btn btn-danger" data-ya>Ya, hapus</button>
                    </div>
                </div>`;
            overlay.querySelector(".modal-message").textContent = pesan;
            document.body.appendChild(overlay);

            const selesai = (hasil) => {
                overlay.remove();
                document.removeEventListener("keydown", onKey);
                resolve(hasil);
            };
            const onKey = (event) => {
                if (event.key === "Escape") selesai(false);
            };

            overlay.querySelector("[data-batal]").addEventListener("click", () => selesai(false));
            overlay.querySelector("[data-ya]").addEventListener("click", () => selesai(true));
            overlay.addEventListener("click", (event) => {
                if (event.target === overlay) selesai(false);
            });
            document.addEventListener("keydown", onKey);
            overlay.querySelector("[data-ya]").focus();
        });
    }

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            if (form.dataset.confirmed) return;
            event.preventDefault();
            if (await tampilkanKonfirmasi(form.dataset.confirm)) {
                form.dataset.confirmed = "true";
                form.submit();
            }
        });
    });

    // ---- Form transaksi ----------------------------------------------------
    document.querySelectorAll("[data-saldo-form]").forEach((form) => {
        const nominalInput = form.querySelector("[data-rupiah]");
        const kategoriInput = form.querySelector("#kategori");
        const jenisInputs = form.querySelectorAll("input[name='jenis']");
        const peringatan = form.querySelector("[data-saldo-warning]");
        const tombolSimpan = form.querySelector("button[type='submit']");
        const saldoAwal = Number(form.dataset.saldoAwal);
        const saldoDasar = Number(form.dataset.saldoDasar);

        const jenisTerpilih = () => {
            const terpilih = form.querySelector("input[name='jenis']:checked");
            return terpilih ? terpilih.value : "";
        };

        function cekSaldo() {
            const nominal = Number(nominalInput.value.replace(/\D/g, "")) || 0;
            const jenis = jenisTerpilih();
            const efek = jenis === "pemasukan" ? nominal : -nominal;
            const saldoAkhir = saldoDasar + efek;
            const melebihi = jenis !== "" && saldoAkhir < 0 && saldoAkhir < saldoAwal;

            peringatan.hidden = !melebihi;
            nominalInput.closest(".input-prefix").classList.toggle("is-invalid", melebihi);
            tombolSimpan.disabled = melebihi;
        }

        function aturSaranKategori() {
            const jenis = jenisTerpilih();
            if (jenis) kategoriInput.setAttribute("list", "kategori-" + jenis);
        }

        nominalInput.addEventListener("input", () => {
            const angka = nominalInput.value.replace(/\D/g, "");
            nominalInput.value = angka === "" ? "" : formatRupiah(angka);
            cekSaldo();
        });

        jenisInputs.forEach((input) => input.addEventListener("change", () => {
            aturSaranKategori();
            cekSaldo();
        }));

        aturSaranKategori();
        cekSaldo();
    });
})();
