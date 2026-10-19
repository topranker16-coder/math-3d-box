```python
import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="입체도형 전개도 3D 조립 교구", layout="wide")

st.title("📦 2D 전개도 3D 인터랙티브 조립 교구")
st.write("2D 모눈종이에 칠한 면들이 3D 공간 상에서 실제로 접히는 모습을 확인해 보세요!")

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

    # 선택된 면 좌표 추출 (행 r, 열 c)
    selected_cells = []
    for r in range(grid_size):
        for c in range(grid_size):
            if st.session_state.grid[r, c] == 1:
                selected_cells.append((r, c))

    st.info(f"현재 선택된 면: **{len(selected_cells)}개**")

# 2. 3D 시뮬레이션 및 폴딩 계산 엔진
with col_right:
    st.subheader("2단계: 3D 조립 시뮬레이션")
    
    fold_angle = st.slider("접는 각도 (0° = 평면, 90° = 완전 접힘)", 0, 90, 0, step=5)
    
    fig = go.Figure()
    
    if len(selected_cells) == 0:
        st.warning("왼쪽 모눈종이에서 최소 1개 이상의 면을 선택해 주세요!")
    else:
        # 가장 첫 번째 선택된 칸을 기준(바닥면)으로 설정
        base_r, base_c = selected_cells[0]
        angle_rad = np.radians(fold_angle)
        
        # 3D 렌더링용 데이터
        mesh_x, mesh_y, mesh_z = [], [], []
        i_list, j_list, k_list = [], [], []
        vert_offset = 0

        for r, c in selected_cells:
            # 기준점 대비 상대적 위치 연산
            dr = r - base_r
            dc = c - base_c
            
            # 접힘 로직 모사 (기준면 주변의 면들이 각도에 맞춰 z축 방향으로 올려짐)
            if dr == 0 and dc == 0:
                # 바닥 기준 면
                x = [c, c+1, c+1, c]
                y = [3-r, 3-r, 4-r, 4-r]
                z = [0, 0, 0, 0]
            else:
                # 주변 면들의 3D 폴딩 꺾임 매핑
                dist = abs(dr) + abs(dc)
                z_lift = np.sin(angle_rad) * min(dist, 1.0)
                shrink = 1.0 - (1.0 - np.cos(angle_rad)) * min(dist, 1.0)
                
                x = [c, c+shrink, c+shrink, c]
                y = [3-r, 3-r, 4-r, 4-r]
                z = [z_lift, z_lift, z_lift, z_lift]

            # 3D 메시 꼭짓점 추가
            mesh_x.extend(x)
            mesh_y.extend(y)
            mesh_z.extend(z)
            
            # 사각형 면을 2개 삼각형 폴리곤으로 매핑
            i_list.extend([vert_offset, vert_offset])
            j_list.extend([vert_offset+1, vert_offset+2])
            k_list.extend([vert_offset+2, vert_offset+3])
            vert_offset += 4

        # 3D 면(Mesh3d) 추가
        fig.add_trace(go.Mesh3d(
            x=mesh_x, y=mesh_y, z=mesh_z,
            i=i_list, j=j_list, k=k_list,
            color='royalblue',
            opacity=0.85,
            flatshading=True,
            name="전개도 면"
        ))

        # 테두리 선(Wireframe) 추가
        for idx in range(0, len(mesh_x), 4):
            fig.add_trace(go.Scatter3d(
                x=mesh_x[idx:idx+4] + [mesh_x[idx]],
                y=mesh_y[idx:idx+4] + [mesh_y[idx]],
                z=mesh_z[idx:idx+4] + [mesh_z[idx]],
                mode='lines',
                line=dict(color='darkblue', width=4),
                showlegend=False
            ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-1, 5], title="X"),
            yaxis=dict(range=[-1, 5], title="Y"),
            zaxis=dict(range=[-1, 4], title="Z"),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)
```

---
