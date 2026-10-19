import streamlit as st
import numpy as np
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(page_title="입체도형 전개도 3D 조립 교구", layout="wide")

st.title("📦 2D 전개도 3D 조립 교구")
st.write("모눈종이 칸을 클릭해 전개도를 만들고, 슬라이더를 움직여 입체로 접어보세요!")

col_left, col_right = st.columns([1, 1])

# 1. 2D 그리드 영역
with col_left:
    st.subheader("1단계: 2D 전개도 칠하기")
    
    grid_size = 4
    if "grid" not in st.session_state:
        st.session_state.grid = np.zeros((grid_size, grid_size), dtype=int)

    for r in range(grid_size):
        cols = st.columns(grid_size)
        for c in range(grid_size):
            val = st.session_state.grid[r, c]
            label = "🟦" if val == 1 else "⬜"
            if cols[c].button(label, key=f"cell_{r}_{c}", use_container_width=True):
                st.session_state.grid[r, c] = 1 - val
                st.rerun()

    if st.button("🔄 전개도 초기화", use_container_width=True):
        st.session_state.grid = np.zeros((grid_size, grid_size), dtype=int)
        st.rerun()

    active_count = int(np.sum(st.session_state.grid))
    st.info(f"현재 선택된 면: **{active_count}개**")

# 2. 3D 시뮬레이션 영역
with col_right:
    st.subheader("2단계: 3D 조립 시뮬레이션")
    
    fold_progress = st.slider("접는 각도", 0, 90, 0, step=5)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=[0, 1, 1, 0, 0, 1, 1, 0],
        y=[0, 0, 1, 1, 0, 0, 1, 1],
        z=[0, 0, 0, 0, 1, 1, 1, 1],
        mode='markers+lines',
        marker=dict(size=8, color=fold_progress, colorscale='Viridis'),
        line=dict(color='darkblue', width=4),
        name="상자"
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-2, 2]),
            yaxis=dict(range=[-2, 2]),
            zaxis=dict(range=[-2, 2]),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)