import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

OUT_DIR = "/home/khoile/Documents/QuizApp/figures"
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

# 1. Fig 2.1: Three-way Handshake
def create_fig_2_1():
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Lifelines
    ax.plot([2.5, 2.5], [1, 7], 'k--', lw=1.5)
    ax.plot([7.5, 7.5], [1, 7], 'k--', lw=1.5)

    # Headers
    ax.text(2.5, 7.3, 'Client', ha='center', va='center', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#e3f2fd', edgecolor='#1976d2', lw=1.5))
    ax.text(7.5, 7.3, 'Server', ha='center', va='center', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#e8f5e9', edgecolor='#388e3c', lw=1.5))

    # Step 1: SYN
    ax.annotate('', xy=(7.4, 5.2), xytext=(2.6, 6.0),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#0288d1'))
    ax.text(5.0, 5.8, '1. SYN (seq = x)', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#01579b')

    # Step 2: SYN + ACK
    ax.annotate('', xy=(2.6, 3.4), xytext=(7.4, 4.2),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#388e3c'))
    ax.text(5.0, 4.0, '2. SYN + ACK (seq = y, ack = x + 1)', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#1b5e20')

    # Step 3: ACK
    ax.annotate('', xy=(7.4, 1.8), xytext=(2.6, 2.6),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#f57c00'))
    ax.text(5.0, 2.4, '3. ACK (ack = y + 1)', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#e65100')

    # Connection established
    ax.text(5.0, 0.8, '== KẾT NỐI ĐƯỢC THIẾT LẬP (ESTABLISHED) ==', ha='center', va='center', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle='square,pad=0.4', facecolor='#fff9c4', edgecolor='#fbc02d', lw=1.2))

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_1_handshake.png"), bbox_inches='tight')
    plt.close(fig)

# 2. Fig 2.2: Byte Stream
def create_fig_2_2():
    fig, ax = plt.subplots(figsize=(7, 3), dpi=200)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis('off')

    # Client Box
    ax.add_patch(patches.Rectangle((0.5, 1.2), 2.5, 2.6, facecolor='#ffcdd2', edgecolor='#d32f2f', lw=1.8))
    ax.text(1.75, 2.5, 'TCP Client', ha='center', va='center', fontsize=11, fontweight='bold', color='#b71c1c')

    # Server Box
    ax.add_patch(patches.Rectangle((9.0, 1.2), 2.5, 2.6, facecolor='#bbdefb', edgecolor='#1976d2', lw=1.8))
    ax.text(10.25, 2.5, 'TCP Server', ha='center', va='center', fontsize=11, fontweight='bold', color='#0d47a1')

    # Top Arrow (Client -> Server)
    ax.annotate('', xy=(8.8, 3.1), xytext=(3.2, 3.1),
                arrowprops=dict(arrowstyle='->', lw=3, color='#2e7d32'))
    ax.text(6.0, 3.3, '010110010101101001110101 (Byte Stream)', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1b5e20')

    # Bottom Arrow (Server -> Client)
    ax.annotate('', xy=(3.2, 1.9), xytext=(8.8, 1.9),
                arrowprops=dict(arrowstyle='->', lw=3, color='#0288d1'))
    ax.text(6.0, 1.3, '101101001011010101001101 (Byte Stream)', ha='center', va='top', fontsize=9, fontweight='bold', color='#01579b')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_2_byte_stream.png"), bbox_inches='tight')
    plt.close(fig)

# 3. Fig 2.3: Socket in TCP/IP
def create_fig_2_3():
    fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Application Layer
    ax.add_patch(patches.Rectangle((1.5, 7.2), 7, 1.2, facecolor='#e1f5fe', edgecolor='#0288d1', lw=1.5))
    ax.text(5, 7.8, 'Chương trình Ứng dụng (Client / Server)', ha='center', va='center', fontsize=10, fontweight='bold')

    # Arrow Down
    ax.annotate('', xy=(5, 6.3), xytext=(5, 7.2), arrowprops=dict(arrowstyle='->', lw=1.5, color='#333333'))

    # Socket Layer
    ax.add_patch(patches.Rectangle((2.5, 5.5), 5, 0.8, facecolor='#ffe082', edgecolor='#ffa000', lw=1.8))
    ax.text(5, 5.9, 'SOCKET API (Giao diện lập trình)', ha='center', va='center', fontsize=10, fontweight='bold')

    # Arrow Down
    ax.annotate('', xy=(5, 4.6), xytext=(5, 5.5), arrowprops=dict(arrowstyle='->', lw=1.5, color='#333333'))

    # Transport Layer
    ax.add_patch(patches.Rectangle((1.5, 3.4), 3.4, 1.2, facecolor='#c8e6c9', edgecolor='#388e3c', lw=1.5))
    ax.text(3.2, 4.0, 'TCP\n(Hướng kết nối, tin cậy)', ha='center', va='center', fontsize=9, fontweight='bold', color='#1b5e20')

    ax.add_patch(patches.Rectangle((5.1, 3.4), 3.4, 1.2, facecolor='#ffcdd2', edgecolor='#d32f2f', lw=1.5))
    ax.text(6.8, 4.0, 'UDP\n(Không kết nối, tốc độ)', ha='center', va='center', fontsize=9, fontweight='bold', color='#b71c1c')

    # Network Layer
    ax.add_patch(patches.Rectangle((1.5, 2.0), 7, 1.0, facecolor='#ede7f6', edgecolor='#512da8', lw=1.5))
    ax.text(5, 2.5, 'IP (Internet Protocol / ICMP / ARP)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#311b92')

    # Link & Physical Layer
    ax.add_patch(patches.Rectangle((1.5, 0.6), 7, 1.0, facecolor='#f5f5f5', edgecolor='#616161', lw=1.5))
    ax.text(5, 1.1, 'Tầng Liên kết & Vật lý (Ethernet / Wi-Fi)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#424242')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_3_socket_layer.png"), bbox_inches='tight')
    plt.close(fig)

# 4. Fig 2.4: Socket Channel
def create_fig_2_4():
    fig, ax = plt.subplots(figsize=(7, 2.6), dpi=200)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # Client
    ax.add_patch(patches.Rectangle((0.5, 1.0), 2.2, 2.0, facecolor='#fce4ec', edgecolor='#c2185b', lw=1.5))
    ax.text(1.6, 2.0, 'Client\nProgram', ha='center', va='center', fontsize=10, fontweight='bold')

    # Client Socket
    ax.add_patch(patches.Rectangle((3.0, 1.2), 1.0, 1.6, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.5))
    ax.text(3.5, 2.0, 'Socket', ha='center', va='center', fontsize=9, fontweight='bold', rotation=90)

    # Server Socket
    ax.add_patch(patches.Rectangle((8.0, 1.2), 1.0, 1.6, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.5))
    ax.text(8.5, 2.0, 'Socket', ha='center', va='center', fontsize=9, fontweight='bold', rotation=90)

    # Server
    ax.add_patch(patches.Rectangle((9.3, 1.0), 2.2, 2.0, facecolor='#e8eaf6', edgecolor='#3f51b5', lw=1.5))
    ax.text(10.4, 2.0, 'Server\nProgram', ha='center', va='center', fontsize=10, fontweight='bold')

    # Connecting Channel
    ax.add_patch(patches.Rectangle((4.0, 1.4), 4.0, 1.2, facecolor='#b3e5fc', edgecolor='#0288d1', lw=1.5))
    ax.text(6.0, 2.0, 'Kênh kết nối TCP ảo (Full-Duplex)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#01579b')

    # Arrows
    ax.annotate('', xy=(3.0, 2.3), xytext=(2.7, 2.3), arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.annotate('', xy=(2.7, 1.7), xytext=(3.0, 1.7), arrowprops=dict(arrowstyle='->', lw=1.5))

    ax.annotate('', xy=(9.3, 2.3), xytext=(9.0, 2.3), arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.annotate('', xy=(9.0, 1.7), xytext=(9.3, 1.7), arrowprops=dict(arrowstyle='->', lw=1.5))

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_4_socket_channel.png"), bbox_inches='tight')
    plt.close(fig)

# 5. Fig 2.5: Server Algorithm
def create_fig_2_5():
    fig, ax = plt.subplots(figsize=(4.5, 6.5), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis('off')

    steps = [
        ("Tạo socket TCP (socket)", 10.0),
        ("Gán địa chỉ IP và Port (bind)", 8.8),
        ("Chờ và lắng nghe (listen)", 7.6),
        ("Có yêu cầu kết nối?", 6.3, "diamond"),
        ("Chấp nhận kết nối (accept)", 4.8),
        ("Gửi / nhận dữ liệu (send/recv)", 3.4),
        ("Tiếp tục phiên?", 2.1, "diamond"),
        ("Đóng kết nối (close)", 0.8)
    ]

    for item in steps:
        text = item[0]
        y = item[1]
        shape = item[2] if len(item) > 2 else "rect"

        if shape == "rect":
            ax.add_patch(patches.Rectangle((1.5, y - 0.4), 7, 0.7, facecolor='#e3f2fd', edgecolor='#1976d2', lw=1.2))
            ax.text(5, y - 0.05, text, ha='center', va='center', fontsize=9, fontweight='bold')
        elif shape == "diamond":
            p = patches.Polygon([[5, y + 0.45], [8.5, y], [5, y - 0.45], [1.5, y]], facecolor='#fff9c4', edgecolor='#fbc02d', lw=1.2)
            ax.add_patch(p)
            ax.text(5, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold')

    # Flow arrows
    ax.annotate('', xy=(5, 9.1), xytext=(5, 9.6), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(5, 7.9), xytext=(5, 8.4), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(5, 6.75), xytext=(5, 7.2), arrowprops=dict(arrowstyle='->', lw=1.2))

    # Diamond 1: yes -> accept
    ax.annotate('', xy=(5, 5.15), xytext=(5, 5.85), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.text(5.2, 5.5, 'Có', fontsize=8, color='green', fontweight='bold')

    # Diamond 1: no -> loop back to listen
    ax.plot([8.5, 9.2, 9.2, 5], [6.3, 6.3, 7.6, 7.6], 'r-', lw=1.0)
    ax.annotate('', xy=(5, 7.6), xytext=(5.2, 7.6), arrowprops=dict(arrowstyle='->', lw=1.2, color='red'))
    ax.text(8.8, 6.4, 'Không', fontsize=7.5, color='red')

    # accept -> send/recv
    ax.annotate('', xy=(5, 3.75), xytext=(5, 4.4), arrowprops=dict(arrowstyle='->', lw=1.2))

    # send/recv -> diamond 2
    ax.annotate('', xy=(5, 2.55), xytext=(5, 3.0), arrowprops=dict(arrowstyle='->', lw=1.2))

    # diamond 2: yes -> loop send/recv
    ax.plot([8.5, 9.2, 9.2, 5], [2.1, 2.1, 3.4, 3.4], 'g-', lw=1.0)
    ax.annotate('', xy=(5, 3.4), xytext=(5.2, 3.4), arrowprops=dict(arrowstyle='->', lw=1.2, color='green'))
    ax.text(8.8, 2.2, 'Có', fontsize=7.5, color='green')

    # diamond 2: no -> close
    ax.annotate('', xy=(5, 1.15), xytext=(5, 1.65), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.text(5.2, 1.4, 'Không', fontsize=8, color='red', fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_5_server_algo.png"), bbox_inches='tight')
    plt.close(fig)

# 6. Fig 2.6: Client Algorithm
def create_fig_2_6():
    fig, ax = plt.subplots(figsize=(4.5, 5.8), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9.5)
    ax.axis('off')

    steps = [
        ("Tạo socket TCP (socket)", 8.7),
        ("Gửi yêu cầu kết nối (connect)", 7.4),
        ("Kết nối thành công?", 6.0, "diamond"),
        ("Gửi / nhận dữ liệu (send/recv)", 4.4),
        ("Tiếp tục trao đổi?", 3.0, "diamond"),
        ("Đóng kết nối (close)", 1.5)
    ]

    for item in steps:
        text = item[0]
        y = item[1]
        shape = item[2] if len(item) > 2 else "rect"

        if shape == "rect":
            ax.add_patch(patches.Rectangle((1.5, y - 0.4), 7, 0.7, facecolor='#e8f5e9', edgecolor='#388e3c', lw=1.2))
            ax.text(5, y - 0.05, text, ha='center', va='center', fontsize=9, fontweight='bold')
        elif shape == "diamond":
            p = patches.Polygon([[5, y + 0.45], [8.5, y], [5, y - 0.45], [1.5, y]], facecolor='#fff9c4', edgecolor='#fbc02d', lw=1.2)
            ax.add_patch(p)
            ax.text(5, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold')

    # Arrows
    ax.annotate('', xy=(5, 7.75), xytext=(5, 8.3), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(5, 6.45), xytext=(5, 7.0), arrowprops=dict(arrowstyle='->', lw=1.2))

    # Diamond 1: yes -> send/recv
    ax.annotate('', xy=(5, 4.75), xytext=(5, 5.55), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.text(5.2, 5.15, 'Có', fontsize=8, color='green', fontweight='bold')

    # Diamond 1: no -> close
    ax.plot([1.5, 0.8, 0.8, 1.5], [6.0, 6.0, 1.5, 1.5], 'r-', lw=1.0)
    ax.annotate('', xy=(1.5, 1.5), xytext=(1.2, 1.5), arrowprops=dict(arrowstyle='->', lw=1.2, color='red'))
    ax.text(0.9, 5.5, 'Không', fontsize=7.5, color='red')

    # send/recv -> diamond 2
    ax.annotate('', xy=(5, 3.45), xytext=(5, 4.0), arrowprops=dict(arrowstyle='->', lw=1.2))

    # diamond 2: yes -> loop send/recv
    ax.plot([8.5, 9.2, 9.2, 5], [3.0, 3.0, 4.4, 4.4], 'g-', lw=1.0)
    ax.annotate('', xy=(5, 4.4), xytext=(5.2, 4.4), arrowprops=dict(arrowstyle='->', lw=1.2, color='green'))
    ax.text(8.8, 3.1, 'Có', fontsize=7.5, color='green')

    # diamond 2: no -> close
    ax.annotate('', xy=(5, 1.85), xytext=(5, 2.55), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.text(5.2, 2.2, 'Không', fontsize=8, color='red', fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_6_client_algo.png"), bbox_inches='tight')
    plt.close(fig)

# 7. Fig 2.7: General Client-Server interaction
def create_fig_2_7():
    fig, ax = plt.subplots(figsize=(7, 6.5), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Client Title
    ax.text(3, 8.5, 'CLIENT PROCESS', ha='center', va='center', fontsize=11, fontweight='bold', color='#1565c0')
    # Server Title
    ax.text(11, 8.5, 'SERVER PROCESS', ha='center', va='center', fontsize=11, fontweight='bold', color='#2e7d32')

    # Client Steps
    c_steps = [
        ("Tạo socket TCP", 7.5),
        ("Gửi yêu cầu connect()", 5.8),
        ("Trao đổi dữ liệu\nsend() / recv()", 3.8),
        ("Đóng socket close()", 1.8)
    ]
    for text, y in c_steps:
        ax.add_patch(patches.Rectangle((0.8, y - 0.45), 4.4, 0.9, facecolor='#e3f2fd', edgecolor='#1976d2', lw=1.2))
        ax.text(3, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold')

    # Server Steps
    s_steps = [
        ("Tạo socket & bind(IP, Port)", 7.5),
        ("Lắng nghe listen() &\nChấp nhận accept()", 5.8),
        ("Trao đổi dữ liệu\nrecv() / send()", 3.8),
        ("Đóng socket con close()", 1.8)
    ]
    for text, y in s_steps:
        ax.add_patch(patches.Rectangle((8.8, y - 0.45), 4.4, 0.9, facecolor='#e8f5e9', edgecolor='#388e3c', lw=1.2))
        ax.text(11, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold')

    # Client internal arrows
    ax.annotate('', xy=(3, 6.25), xytext=(3, 7.05), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(3, 4.25), xytext=(3, 5.35), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(3, 2.25), xytext=(3, 3.35), arrowprops=dict(arrowstyle='->', lw=1.2))

    # Server internal arrows
    ax.annotate('', xy=(11, 6.25), xytext=(11, 7.05), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(11, 4.25), xytext=(11, 5.35), arrowprops=dict(arrowstyle='->', lw=1.2))
    ax.annotate('', xy=(11, 2.25), xytext=(11, 3.35), arrowprops=dict(arrowstyle='->', lw=1.2))

    # Cross interaction arrows
    # Connect
    ax.annotate('', xy=(8.8, 5.9), xytext=(5.2, 5.9),
                arrowprops=dict(arrowstyle='->', lw=1.6, color='#d32f2f'))
    ax.text(7.0, 6.1, 'Three-way Handshake', ha='center', fontsize=8, color='#b71c1c', fontweight='bold')

    # Data request
    ax.annotate('', xy=(8.8, 4.1), xytext=(5.2, 4.1),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#1976d2'))
    ax.text(7.0, 4.3, 'Request (JSON + 4-byte)', ha='center', fontsize=7.5, color='#0d47a1', fontweight='bold')

    # Data response
    ax.annotate('', xy=(5.2, 3.5), xytext=(8.8, 3.5),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#388e3c'))
    ax.text(7.0, 3.1, 'Response (JSON + 4-byte)', ha='center', fontsize=7.5, color='#1b5e20', fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_7_general_algo.png"), bbox_inches='tight')
    plt.close(fig)

# 8. Fig 2.8: Server Streams
def create_fig_2_8():
    fig, ax = plt.subplots(figsize=(7, 2.5), dpi=200)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # TCP Channel
    ax.add_patch(patches.Rectangle((0.5, 1.0), 4.5, 2.0, facecolor='#b3e5fc', edgecolor='#0288d1', lw=1.5))
    ax.text(2.75, 2.0, 'Kênh kết nối TCP\n(Stream Socket)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#01579b')

    # Server Socket
    ax.add_patch(patches.Rectangle((5.5, 0.8), 1.0, 2.4, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.5))
    ax.text(6.0, 2.0, 'Socket', ha='center', va='center', fontsize=9, fontweight='bold', rotation=90)

    # Server
    ax.add_patch(patches.Rectangle((8.5, 0.5), 3.0, 3.0, facecolor='#e8f5e9', edgecolor='#388e3c', lw=1.8))
    ax.text(10.0, 2.0, 'Server\nProcess', ha='center', va='center', fontsize=11, fontweight='bold', color='#1b5e20')

    # InputStream (Channel -> Server)
    ax.add_patch(patches.Rectangle((6.7, 2.3), 1.6, 0.6, facecolor='#c8e6c9', edgecolor='#43a047', lw=1.2))
    ax.text(7.5, 2.6, 'InputStream', ha='center', va='center', fontsize=8, fontweight='bold', color='#1b5e20')
    ax.annotate('', xy=(8.4, 2.6), xytext=(6.5, 2.6), arrowprops=dict(arrowstyle='->', lw=1.5, color='#2e7d32'))

    # OutputStream (Server -> Channel)
    ax.add_patch(patches.Rectangle((6.7, 1.1), 1.6, 0.6, facecolor='#ffcdd2', edgecolor='#e53935', lw=1.2))
    ax.text(7.5, 1.4, 'OutputStream', ha='center', va='center', fontsize=8, fontweight='bold', color='#b71c1c')
    ax.annotate('', xy=(6.5, 1.4), xytext=(8.4, 1.4), arrowprops=dict(arrowstyle='->', lw=1.5, color='#c62828'))

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_8_server_streams.png"), bbox_inches='tight')
    plt.close(fig)

# 9. Fig 2.9: Client Streams
def create_fig_2_9():
    fig, ax = plt.subplots(figsize=(7, 2.5), dpi=200)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # Client
    ax.add_patch(patches.Rectangle((0.5, 0.5), 3.0, 3.0, facecolor='#e3f2fd', edgecolor='#1976d2', lw=1.8))
    ax.text(2.0, 2.0, 'Client\nProcess', ha='center', va='center', fontsize=11, fontweight='bold', color='#0d47a1')

    # Client Socket
    ax.add_patch(patches.Rectangle((4.5, 0.8), 1.0, 2.4, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.5))
    ax.text(5.0, 2.0, 'Socket', ha='center', va='center', fontsize=9, fontweight='bold', rotation=90)

    # TCP Channel
    ax.add_patch(patches.Rectangle((6.0, 1.0), 4.5, 2.0, facecolor='#b3e5fc', edgecolor='#0288d1', lw=1.5))
    ax.text(8.25, 2.0, 'Kênh kết nối TCP\n(Stream Socket)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#01579b')

    # OutputStream (Client -> Channel)
    ax.add_patch(patches.Rectangle((3.1, 2.3), 1.2, 0.6, facecolor='#ffcdd2', edgecolor='#e53935', lw=1.2))
    ax.text(3.7, 2.6, 'OutputStream', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#b71c1c')
    ax.annotate('', xy=(4.4, 2.6), xytext=(3.0, 2.6), arrowprops=dict(arrowstyle='->', lw=1.5, color='#c62828'))

    # InputStream (Channel -> Client)
    ax.add_patch(patches.Rectangle((3.1, 1.1), 1.2, 0.6, facecolor='#c8e6c9', edgecolor='#43a047', lw=1.2))
    ax.text(3.7, 1.4, 'InputStream', ha='center', va='center', fontsize=7.5, fontweight='bold', color='#1b5e20')
    ax.annotate('', xy=(3.0, 1.4), xytext=(4.4, 1.4), arrowprops=dict(arrowstyle='->', lw=1.5, color='#2e7d32'))

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_9_client_streams.png"), bbox_inches='tight')
    plt.close(fig)

# 10. Fig 2.10: Multi-threaded server overview
def create_fig_2_10():
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=200)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # Server Box
    ax.add_patch(patches.Rectangle((0.5, 0.8), 3.2, 5.4, facecolor='#ede7f6', edgecolor='#512da8', lw=1.8))
    ax.text(2.1, 5.7, 'Server Process\n(QuizServer)', ha='center', va='center', fontsize=11, fontweight='bold', color='#311b92')

    # Server Threads
    threads = [("Thread 1 (Worker)", 4.5), ("Thread 2 (Worker)", 3.2), ("Thread 3 (Worker)", 1.9)]
    for name, y in threads:
        ax.add_patch(patches.Rectangle((0.8, y - 0.4), 2.6, 0.8, facecolor='#d1c4e9', edgecolor='#7e57c2', lw=1.2))
        ax.text(2.1, y, name, ha='center', va='center', fontsize=9, fontweight='bold', color='#311b92')

    # Clients
    clients = [("Client 1 (Admin)", 4.5), ("Client 2 (Teacher)", 3.2), ("Client 3 (Student)", 1.9)]
    for name, y in clients:
        ax.add_patch(patches.Rectangle((8.5, y - 0.4), 3.0, 0.8, facecolor='#e1f5fe', edgecolor='#0288d1', lw=1.2))
        ax.text(10.0, y, name, ha='center', va='center', fontsize=9, fontweight='bold', color='#01579b')

        # Connection arrow
        ax.annotate('', xy=(8.4, y), xytext=(3.5, y), arrowprops=dict(arrowstyle='<->', lw=2.0, color='#00796b'))
        ax.text(6.0, y + 0.15, 'TCP Socket Kênh riêng', ha='center', va='bottom', fontsize=7.5, color='#004d40', fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_10_multithread_overview.png"), bbox_inches='tight')
    plt.close(fig)

# 11. Fig 2.11: Multi-threaded server detail
def create_fig_2_11():
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # Clients on left
    c_y = [5.0, 2.0]
    for idx, y in enumerate(c_y, 1):
        ax.add_patch(patches.Rectangle((0.5, y - 0.8), 2.2, 1.6, facecolor='#e3f2fd', edgecolor='#1976d2', lw=1.4))
        ax.text(1.6, y, f'Client {idx}', ha='center', va='center', fontsize=10, fontweight='bold', color='#0d47a1')

        # Client Socket
        ax.add_patch(patches.Rectangle((3.0, y - 0.6), 0.8, 1.2, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.2))
        ax.text(3.4, y, 'Socket', ha='center', va='center', fontsize=7.5, fontweight='bold', rotation=90)

        # Connection channel
        ax.add_patch(patches.Rectangle((4.0, y - 0.5), 3.5, 1.0, facecolor='#b3e5fc', edgecolor='#0288d1', lw=1.2))
        ax.text(5.75, y, f'Kênh kết nối TCP {idx}', ha='center', va='center', fontsize=8, fontweight='bold', color='#01579b')

        # Server Socket
        ax.add_patch(patches.Rectangle((7.7, y - 0.6), 0.8, 1.2, facecolor='#fff59d', edgecolor='#fbc02d', lw=1.2))
        ax.text(8.1, y, 'Socket', ha='center', va='center', fontsize=7.5, fontweight='bold', rotation=90)

        # Server Thread
        ax.add_patch(patches.Rectangle((9.5, y - 0.6), 2.2, 1.2, facecolor='#d1c4e9', edgecolor='#7e57c2', lw=1.2))
        ax.text(10.6, y, f'Thread {idx}\n(ClientHandler)', ha='center', va='center', fontsize=8, fontweight='bold', color='#311b92')

        # In/Out streams
        ax.annotate('', xy=(9.4, y + 0.25), xytext=(8.6, y + 0.25), arrowprops=dict(arrowstyle='->', lw=1.2, color='#2e7d32'))
        ax.annotate('', xy=(8.6, y - 0.25), xytext=(9.4, y - 0.25), arrowprops=dict(arrowstyle='->', lw=1.2, color='#c62828'))

    # Big Server Container
    ax.add_patch(patches.Rectangle((9.0, 0.5), 4.5, 6.0, fill=False, edgecolor='#512da8', lw=2, linestyle=':'))
    ax.text(11.25, 6.2, 'Server Process (Multi-threaded)', ha='center', va='center', fontsize=10, fontweight='bold', color='#311b92')

    # Main Accept Loop
    ax.text(12.8, 3.5, 'Main Loop:\naccept()\n--> create Thread', ha='center', va='center', fontsize=8, color='#4527a0',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#ede7f6', edgecolor='#b39ddb'))

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_11_multithread_detail.png"), bbox_inches='tight')
    plt.close(fig)

# 12. Fig 2.12: QuizApp 3-tier architecture
def create_fig_2_12():
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # Tier 1: Client
    ax.add_patch(patches.Rectangle((0.5, 1.0), 3.5, 5.0, facecolor='#e1f5fe', edgecolor='#0288d1', lw=1.8))
    ax.text(2.25, 5.6, 'TIER 1: CLIENT GUI\n(CustomTkinter)', ha='center', va='center', fontsize=10, fontweight='bold', color='#01579b')
    ax.text(2.25, 4.4, '• Admin Dashboard\n• Teacher Dashboard\n• Student Dashboard', ha='center', va='center', fontsize=8.5)
    ax.text(2.25, 2.2, 'ServerConnection\n(Thread-safe Socket,\nLength-prefix framing)', ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#b3e5fc', edgecolor='#0288d1'))

    # Tier 2: Server
    ax.add_patch(patches.Rectangle((5.2, 1.0), 4.0, 5.0, facecolor='#ede7f6', edgecolor='#512da8', lw=1.8))
    ax.text(7.2, 5.6, 'TIER 2: QUIZ SERVER\n(TCP Multi-threaded)', ha='center', va='center', fontsize=10, fontweight='bold', color='#311b92')
    ax.text(7.2, 4.4, '• QuizServer (Port 9999)\n• ClientHandler Threads\n• AuthService (Bcrypt)\n• Service Layer (Exam/Ques)', ha='center', va='center', fontsize=8)
    ax.text(7.2, 2.2, 'DAO Layer\n(PyMySQL Connection Pool,\nPrepared SQL Queries)', ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#d1c4e9', edgecolor='#7e57c2'))

    # Tier 3: Database
    ax.add_patch(patches.Rectangle((10.4, 1.0), 3.1, 5.0, facecolor='#e8f5e9', edgecolor='#388e3c', lw=1.8))
    ax.text(11.95, 5.6, 'TIER 3: DATABASE\n(MySQL 8.0 Docker)', ha='center', va='center', fontsize=10, fontweight='bold', color='#1b5e20')
    ax.text(11.95, 3.8, 'Database: quiz_app\n\n• users\n• subjects\n• questions\n• exams\n• exam_questions\n• exam_results\n• exam_answers', ha='center', va='center', fontsize=8)
    ax.text(11.95, 1.7, 'Storage: InnoDB\nCharset: utf8mb4', ha='center', va='center', fontsize=7.5, color='#2e7d32')

    # Arrow Tier 1 <-> Tier 2
    ax.annotate('', xy=(5.1, 3.5), xytext=(4.1, 3.5), arrowprops=dict(arrowstyle='<->', lw=2.2, color='#0288d1'))
    ax.text(4.6, 3.8, 'TCP Socket\nPort 9999', ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#01579b')

    # Arrow Tier 2 <-> Tier 3
    ax.annotate('', xy=(10.3, 3.5), xytext=(9.3, 3.5), arrowprops=dict(arrowstyle='<->', lw=2.2, color='#388e3c'))
    ax.text(9.8, 3.8, 'TCP / SQL\nPort 3306', ha='center', va='bottom', fontsize=7.5, fontweight='bold', color='#1b5e20')

    plt.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "fig_2_12_quizapp_architecture.png"), bbox_inches='tight')
    plt.close(fig)

print("Creating all 12 figures...")
create_fig_2_1()
create_fig_2_2()
create_fig_2_3()
create_fig_2_4()
create_fig_2_5()
create_fig_2_6()
create_fig_2_7()
create_fig_2_8()
create_fig_2_9()
create_fig_2_10()
create_fig_2_11()
create_fig_2_12()
print("All 12 figures created successfully in", OUT_DIR)
