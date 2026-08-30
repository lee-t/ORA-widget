FROM ghcr.io/astral-sh/uv@sha256:e1869b1ddae289d6aa3c76649d0b663c11cb3215371146bf7dce95c821935fea

ENV HOME=/root \
    APP_PYTHON_VERSION=3.14.6 \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    OPENRA_RELEASE=release-20250330 \
    OPENRA_APPIMAGE_SHA256=b3d202d1bf701be5989c41c256d19bd2b1788694df01e343ade865cf1190706b \
    CNC_CONTENT_URL=https://republic.community/hosted/files/command-and-conquer/openra/cnc-packages.zip \
    CNC_CONTENT_SHA256=a55b2c160b534f6d1b865ad6120e1f4fde8c418d47bb2fb1a9c72c586a5e1603 \
    PORT=2718

RUN test "$(uname -m)" = x86_64 \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        ffmpeg \
        libgl1 \
        libgl1-mesa-dri \
        libopenal1 \
        libsdl2-2.0-0 \
        procps \
        unzip \
        x11-utils \
        xdotool \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/uv.lock /tmp/uv.lock
RUN uv pip install --system --require-hashes --no-cache -r /tmp/uv.lock \
    && rm /tmp/uv.lock

# The lock is generated for Python 3.14 on Linux amd64 and includes hashes.
COPY requirements.lock /tmp/requirements.lock
RUN uv python install "$APP_PYTHON_VERSION" --install-dir "$UV_PYTHON_INSTALL_DIR" \
    && uv pip install \
        --python "$UV_PYTHON_INSTALL_DIR/cpython-${APP_PYTHON_VERSION}-linux-x86_64-gnu/bin/python" \
        --break-system-packages \
        --require-hashes --no-cache -r /tmp/requirements.lock \
    && "$UV_PYTHON_INSTALL_DIR/cpython-${APP_PYTHON_VERSION}-linux-x86_64-gnu/bin/python" \
        -c 'import sys; assert sys.version_info[:3] == (3, 14, 6)' \
    && rm /tmp/requirements.lock

ENV PATH="/opt/uv-python/cpython-3.14.6-linux-x86_64-gnu/bin:${PATH}"

COPY . /app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 2718
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
