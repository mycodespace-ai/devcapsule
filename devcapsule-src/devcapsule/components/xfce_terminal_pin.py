"""Xfce Terminal and its additional Ubuntu Noble packages for the recipe-11 base.

Versions and SHA-256 values come from APT's signed noble, noble-updates and
noble-security indexes. The lock records the complete selected package URLs.
"""

from typing import Any

AMD64: dict[str, Any] = {
    "version": "1.1.3",
    "package-version": "1.1.3-1build1",
    "delivery-policy": "local-materialization",
    "url": "https://archive.ubuntu.com/ubuntu/pool/universe/x/xfce4-terminal/xfce4-terminal_1.1.3-1build1_amd64.deb",
    "sha256": "07c3aca818d694284444b2f65f435c468731aacc94730b5f07d41bc7c313d08a",
    "native-packages": {
        "exo-utils": {
            "version": "4.18.0-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/exo-utils_4.18.0-1build4_amd64.deb",
            "sha256": "25c3a288664e28d30fbff9c2a84b95bef238b58126671e2940dcceaecfff2057",
        },
        "libexo-2-0": {
            "version": "4.18.0-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/libexo-2-0_4.18.0-1build4_amd64.deb",
            "sha256": "0ec42a8bf5f03a5cfbabe707efa491a4816dab5ca217f31ede4975fa8034a1c0",
        },
        "libexo-common": {
            "version": "4.18.0-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/libexo-common_4.18.0-1build4_all.deb",
            "sha256": "c9cd9342c43438688735ba99e8cb469d751a7df82aa4e2145c124bac1afced43",
        },
        "libutempter0": {
            "version": "1.2.1-3build1",
            "url": "https://archive.ubuntu.com/ubuntu/pool/main/libu/libutempter/libutempter0_1.2.1-3build1_amd64.deb",
            "sha256": "46c0dfbfeca19ba0773398d654b7e7225b178f26b414f0e2f8250519551bfb32",
        },
        "libvte-2.91-0": {
            "version": "0.76.0-1ubuntu0.1",
            "url": "https://archive.ubuntu.com/ubuntu/pool/main/v/vte2.91/libvte-2.91-0_0.76.0-1ubuntu0.1_amd64.deb",
            "sha256": "48a0aa9de99fdcdbcabf3a74f4c4f4072ce561c3e2c76ac349d4439a205d04c4",
        },
        "libvte-2.91-common": {
            "version": "0.76.0-1ubuntu0.1",
            "url": "https://archive.ubuntu.com/ubuntu/pool/main/v/vte2.91/libvte-2.91-common_0.76.0-1ubuntu0.1_amd64.deb",
            "sha256": "83b9048ec660d2a6078e4ee7bcad51c116e69645a6e78372736115db4d2bacaa",
        },
        "libxfce4ui-2-0": {
            "version": "4.18.4-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4ui/libxfce4ui-2-0_4.18.4-1build4_amd64.deb",
            "sha256": "d69bb6f2914e44dd7689d0dc5c1b57707f26438ac3a20eb7dc32a3dcf3f1f4cf",
        },
        "libxfce4ui-common": {
            "version": "4.18.4-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4ui/libxfce4ui-common_4.18.4-1build4_all.deb",
            "sha256": "c94cf48cba0477d302fa52d86a791030497f0ff204cda849eede7c3d74cb782a",
        },
        "libxfce4util-common": {
            "version": "4.18.1-2build3",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4util/libxfce4util-common_4.18.1-2build3_all.deb",
            "sha256": "f6ea07adc2d95963127ca0f4ef765076dbe344cc383c5497bd12a527740bb7af",
        },
        "libxfce4util7": {
            "version": "4.18.1-2build3",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4util/libxfce4util7_4.18.1-2build3_amd64.deb",
            "sha256": "31fe7584e10e3ad3d9561855bd32988ccd0388873d4ff02ab33c166948577177",
        },
        "libxfconf-0-3": {
            "version": "4.18.1-1build3",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/x/xfconf/libxfconf-0-3_4.18.1-1build3_amd64.deb",
            "sha256": "1f6732991668251f3c1933486be204bbde4b9d9cdbe7b465eb47178c0da54d4d",
        },
        "xfconf": {
            "version": "4.18.1-1build3",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/x/xfconf/xfconf_4.18.1-1build3_amd64.deb",
            "sha256": "5ed8855e8daa4b278ed5ab9cb8850a031e7633945bbd48fc3fc5a77612f6fd0b",
        },
    },
}

ARM64: dict[str, Any] = {
    "version": "1.1.3",
    "package-version": "1.1.3-1build1",
    "delivery-policy": "local-materialization",
    "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/x/xfce4-terminal/xfce4-terminal_1.1.3-1build1_arm64.deb",
    "sha256": "b6dd5499347d96794091f07c33322ea5d7ac10f444f95c14bfdd9c677ab69741",
    "native-packages": {
        "exo-utils": {
            "version": "4.18.0-1build4",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/e/exo/exo-utils_4.18.0-1build4_arm64.deb",
            "sha256": "9c75b5981af8b05c33549b9179524120a91385d42fe08955e19a46af82ea0f02",
        },
        "libexo-2-0": {
            "version": "4.18.0-1build4",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/e/exo/libexo-2-0_4.18.0-1build4_arm64.deb",
            "sha256": "3e8ec9c3043bb014f0ec243f3d1b6a3354b303ba0957b6f329884a7e6964f530",
        },
        "libexo-common": {
            "version": "4.18.0-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/libexo-common_4.18.0-1build4_all.deb",
            "sha256": "c9cd9342c43438688735ba99e8cb469d751a7df82aa4e2145c124bac1afced43",
        },
        "libutempter0": {
            "version": "1.2.1-3build1",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/main/libu/libutempter/libutempter0_1.2.1-3build1_arm64.deb",
            "sha256": "ba9c2f6b051d47fe3b34dbeac8fe34ac87853dd34eae1492aa034e56de511186",
        },
        "libvte-2.91-0": {
            "version": "0.76.0-1ubuntu0.1",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/main/v/vte2.91/libvte-2.91-0_0.76.0-1ubuntu0.1_arm64.deb",
            "sha256": "3699698e60906a84cf67f47d64a0ad62fd9089a5e3346e7f66b7ca995a229a2b",
        },
        "libvte-2.91-common": {
            "version": "0.76.0-1ubuntu0.1",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/main/v/vte2.91/libvte-2.91-common_0.76.0-1ubuntu0.1_arm64.deb",
            "sha256": "616b622a61a3abbc2c710a7b7e7231833bc86914487ce276b3ff6d5c09e981dd",
        },
        "libxfce4ui-2-0": {
            "version": "4.18.4-1build4",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/libx/libxfce4ui/libxfce4ui-2-0_4.18.4-1build4_arm64.deb",
            "sha256": "b00ab7ca5505c620962e205b5f0f60c7f759219506bcda3ae7680693c8fb85e2",
        },
        "libxfce4ui-common": {
            "version": "4.18.4-1build4",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4ui/libxfce4ui-common_4.18.4-1build4_all.deb",
            "sha256": "c94cf48cba0477d302fa52d86a791030497f0ff204cda849eede7c3d74cb782a",
        },
        "libxfce4util-common": {
            "version": "4.18.1-2build3",
            "url": "https://archive.ubuntu.com/ubuntu/pool/universe/libx/libxfce4util/libxfce4util-common_4.18.1-2build3_all.deb",
            "sha256": "f6ea07adc2d95963127ca0f4ef765076dbe344cc383c5497bd12a527740bb7af",
        },
        "libxfce4util7": {
            "version": "4.18.1-2build3",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/libx/libxfce4util/libxfce4util7_4.18.1-2build3_arm64.deb",
            "sha256": "097a4cc50b65dd436c8586485cc12791e10ad8b7decdcb9b735548ca383883ce",
        },
        "libxfconf-0-3": {
            "version": "4.18.1-1build3",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/x/xfconf/libxfconf-0-3_4.18.1-1build3_arm64.deb",
            "sha256": "efc063565e610412ed51aec8873154a15dd3779526d6e8c40406fb486e5da038",
        },
        "xfconf": {
            "version": "4.18.1-1build3",
            "url": "https://ports.ubuntu.com/ubuntu-ports/pool/universe/x/xfconf/xfconf_4.18.1-1build3_arm64.deb",
            "sha256": "8c080a32614fadbb25080a7e84c9735b3c7cb47f9a54a43090af18788caae78c",
        },
    },
}
