import streamlit as st
import numpy as np
import plotly.graph_objects as go
from collections import deque

st.set_page_config(page_title="입체도형 전개도 3D 조립 교구", layout="wide")

st.title("📦 2D 전개도 3D 정밀 조립 교구")
st.write("2D 모눈종이에 칠한 면들이 실제 종이 상자처럼 변(Hinge)을 축으로 접히는 모습을 확인해 보세요!")

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

    selected_cells = []
    for r in range(grid_size):
        for c in range(grid_size):
            if st.session_state.grid[r, c] == 1:
                selected_cells.append((r, c))

    st.info(f"현재 선택된 면: **{len(selected_cells)}개**")

# 2. 정밀 3D 조립 및 회전 알고리즘
def get_3d_rotation(vertices, hinge_p1, hinge_p2, angle_rad):
    u = hinge_p2 - hinge_p1
    u = u / np.linalg.norm(u)
    
    ux, uy, uz = u
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    R = np.array([
        [cos_a + ux**2*(1-cos_a), ux*uy*(1-cos_a) - uz*sin_a, ux*uz*(1-cos_a) + uy*sin_a],
        [uy*ux*(1-cos_a) + uz*sin_a, cos_a + uy**2*(1-cos_a), uy*uz*(1-cos_a) - ux*sin_a],
        [uz*ux*(1-cos_a) - uy*sin_a, uz*uy*(1-cos_a) + ux*sin_a, cos_a + uz**2*(1-cos_a)]
    ])
    
    rotated_verts = []
    for v in vertices:
        v_trans = v - hinge_p1
        v_rot = np.dot(R, v_trans)
        rotated_verts.append(v_rot + hinge_p1)
        
    return np.array(rotated_verts)

with col_right:
    st.subheader("2단계: 3D 정밀 조립 시뮬레이션")
    
    fold_angle = st.slider("접는 각도 (0° = 평면, 90° = 직각 접힘)", 0, 90, 0, step=5)
    
    fig = go.Figure()
    
    if len(selected_cells) == 0:
        st.warning("왼쪽 모눈종이에서 최소 1개 이상의 면을 선택해 주세요!")
    else:
        cell_set = set(selected_cells)
        base_cell = selected_cells[0]
        
        tree = []
        visited = {base_cell}
        queue = deque([base_cell])
        parent_map = {}
        
        while queue:
            curr = queue.popleft()
            r, c = curr
            neighbors = [
                ((r-1, c), 'UP'), ((r+1, c), 'DOWN'),
                ((r, c-1), 'LEFT'), ((r, c+1), 'RIGHT')
            ]
            for nxt, dir_type in neighbors:
                if nxt in cell_set and nxt not in visited:
                    visited.add(nxt)
                    parent_map[nxt] = (curr, dir_type)
                    queue.append(nxt)
                    tree.append((nxt, curr, dir_type))

        def get_initial_vertices(r, c):
            return np.array([
                [c, 3-r, 0],
                [c+1, 3-r, 0],
                [c+1, 4-r, 0],
                [c, 4-r, 0]
            ], dtype=float)

        angle_rad = np.radians(fold_angle)
        transformed_verts = {}
        transformed_verts[base_cell] = get_initial_vertices(*base_cell)
        
        for child, parent, dir_type in tree:
            p_verts = transformed_verts[parent]
            if dir_type == 'UP':
                hinge_p1, hinge_p2 = p_verts[3], p_verts[2]
            elif dir_type == 'DOWN':
                hinge_p1, hinge_p2 = p_verts[1], p_verts[0]
            elif dir_type == 'LEFT':
                hinge_p1, hinge_p2 = p_verts[0], p_verts[3]
            elif dir_type == 'RIGHT':
                hinge_p1, hinge_p2 = p_verts[2], p_verts[1]

            c_verts = get_initial_vertices(*child)
            rotated = get_3d_rotation(c_verts, hinge_p1, hinge_p2, angle_rad)
            transformed_verts[child] = rotated

        mesh_x, mesh_y, mesh_z = [], [], []
        i_list, j_list, k_list = [], [], []
        vert_offset = 0

        for cell, verts in transformed_verts.items():
            for v in verts:
                mesh_x.append(v[0])
                mesh_y.append(v[1])
                mesh_z.append(v[2])
            
            i_list.extend([vert_offset, vert_offset])
            j_list.extend([vert_offset+1, vert_offset+2])
            k_list.extend([vert_offset+2, vert_offset+3])
            vert_offset += 4

            fig.add_trace(go.Scatter3d(
                x=list(verts[:, 0]) + [verts[0, 0]],
                y=list(verts[:, 1]) + [verts[0, 1]],
                z=list(verts[:, 2]) + [verts[0, 2]],
                mode='lines',
                line=dict(color='darkblue', width=5),
                showlegend=False
            ))

        fig.add_trace(go.Mesh3d(
            x=mesh_x, y=mesh_y, z=mesh_z,
            i=i_list, j=j_list, k=k_list,
            color='dodgerblue',
            opacity=0.8,
            flatshading=True,
            name="면"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-1, 5], title="X"),
            yaxis=dict(range=[-1, 5], title="Y"),
            zaxis=dict(range=[-1, 5], title="Z"),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)
