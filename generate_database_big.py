import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from sklearn.preprocessing import MinMaxScaler
import warnings

warnings.filterwarnings('ignore')


def load_original_data():
    """加载原始数据"""
    # 加载需求点数据
    dp = gpd.read_file("data/EF_data/Demand-1312.shp")
    dp['POINT_X'] = dp.geometry.x
    dp['POINT_Y'] = dp.geometry.y
    dp['demand'] = dp.mianji

    # 加载候选点数据
    cp = pd.read_csv("data/EF_data/候选点.csv")

    print(f"原始数据规模：")
    print(f"需求点 (dp): {len(dp)} 个")
    print(f"候选点 (cp): {len(cp)} 个")
    print(f"总需求量: {dp['demand'].sum():.2f}")

    return dp, cp


def normalize_data(data, columns_to_normalize):
    """
    归一化指定的列到[0, 1]范围
    返回归一化后的数据和scaler对象（用于反归一化）
    """
    scaler = MinMaxScaler()
    data_normalized = data.copy()

    # 只归一化数值列
    numeric_cols = [col for col in columns_to_normalize if col in data.columns]
    if numeric_cols:
        data_normalized[numeric_cols] = scaler.fit_transform(data[numeric_cols])

    return data_normalized, scaler, numeric_cols


def interpolate_points(data, n_target, columns_to_interpolate, random_state=42):
    """
    通过线性插值生成新的数据点

    参数:
    - data: 原始数据（已归一化）
    - n_target: 目标数据点数量
    - columns_to_interpolate: 需要插值的列
    - random_state: 随机种子
    """
    np.random.seed(random_state)
    n_original = len(data)
    n_new = n_target - n_original

    if n_new <= 0:
        print(f"警告：目标数量({n_target})小于原始数量({n_original})，返回原始数据")
        return data

    # 生成新数据点
    new_points = []

    for _ in range(n_new):
        # 随机选择两个不同的原始点
        idx1, idx2 = np.random.choice(n_original, 2, replace=False)
        point1 = data.iloc[idx1]
        point2 = data.iloc[idx2]

        # 随机生成插值权重
        alpha = np.random.random()

        # 对每个需要插值的列进行线性插值
        new_point = {}
        for col in columns_to_interpolate:
            if col in data.columns:
                new_point[col] = alpha * point1[col] + (1 - alpha) * point2[col]

        # 保留非插值列的值（从其中一个点随机选择）
        for col in data.columns:
            if col not in columns_to_interpolate and col not in new_point:
                new_point[col] = point1[col] if np.random.random() < 0.5 else point2[col]

        new_points.append(new_point)

    # 创建新数据框
    new_data = pd.DataFrame(new_points)

    # 合并原始数据和新数据
    expanded_data = pd.concat([data, new_data], ignore_index=True)

    # 随机打乱数据顺序
    expanded_data = expanded_data.sample(frac=1, random_state=random_state).reset_index(drop=True)

    return expanded_data


def denormalize_data(data_normalized, scaler, columns):
    """反归一化数据回原始尺度"""
    data_denormalized = data_normalized.copy()
    if columns:
        data_denormalized[columns] = scaler.inverse_transform(data_normalized[columns])
    return data_denormalized


def expand_demand_points(dp_original, target_count=10000, random_state=42):
    """
    扩充需求点数据
    """
    print(f"\n开始扩充需求点数据...")
    print(f"目标：从 {len(dp_original)} 扩充到 {target_count} 个点")

    # 需要归一化和插值的列
    columns_to_normalize = ['POINT_X', 'POINT_Y', 'demand']

    # 归一化
    dp_normalized, scaler, normalized_cols = normalize_data(dp_original, columns_to_normalize)

    # 插值扩充
    dp_expanded_normalized = interpolate_points(
        dp_normalized,
        target_count,
        columns_to_normalize,
        random_state=random_state
    )

    # 反归一化
    dp_expanded = denormalize_data(dp_expanded_normalized, scaler, normalized_cols)

    # 重建geometry列
    dp_expanded['geometry'] = dp_expanded.apply(
        lambda row: Point(row['POINT_X'], row['POINT_Y']), axis=1
    )

    # 转换为GeoDataFrame
    dp_expanded = gpd.GeoDataFrame(dp_expanded, geometry='geometry', crs=dp_original.crs)

    # 确保demand为正数
    dp_expanded['demand'] = np.abs(dp_expanded['demand'])

    # 调整总需求量与原始数据保持一致
    original_total_demand = dp_original['demand'].sum()
    expanded_total_demand = dp_expanded['demand'].sum()
    demand_scale_factor = original_total_demand / expanded_total_demand
    dp_expanded['demand'] = dp_expanded['demand'] * demand_scale_factor

    print(f"扩充完成：生成 {len(dp_expanded)} 个需求点")
    print(f"总需求量保持：{dp_expanded['demand'].sum():.2f}")

    return dp_expanded


def expand_candidate_points(cp_original, target_count=1000, random_state=42):
    """
    扩充候选点数据
    """
    print(f"\n开始扩充候选点数据...")
    print(f"目标：从 {len(cp_original)} 扩充到 {target_count} 个点")

    # 只对 POINT_X 和 POINT_Y 进行归一化和插值
    columns_to_normalize = ['POINT_X', 'POINT_Y']

    # 检查这些列是否存在
    missing_cols = [col for col in columns_to_normalize if col not in cp_original.columns]
    if missing_cols:
        print(f"警告：候选点数据中缺少列: {missing_cols}")
        return cp_original

    # 归一化
    cp_normalized, scaler, normalized_cols = normalize_data(cp_original, columns_to_normalize)

    # 插值扩充（只对坐标进行插值）
    cp_expanded_normalized = interpolate_points(
        cp_normalized,
        target_count,
        columns_to_normalize,  # 只插值 POINT_X 和 POINT_Y
        random_state=random_state
    )

    # 反归一化
    cp_expanded = denormalize_data(cp_expanded_normalized, scaler, normalized_cols)

    print(f"扩充完成：生成 {len(cp_expanded)} 个候选点")
    print(f"插值列: {columns_to_normalize}")

    return cp_expanded


def validate_expanded_data(dp_original, dp_expanded, cp_original, cp_expanded):
    """
    验证扩充后的数据质量
    """
    print("\n=== 数据验证报告 ===")

    # 需求点验证
    print("\n需求点数据:")
    print(f"  原始数量: {len(dp_original)}")
    print(f"  扩充后数量: {len(dp_expanded)}")
    print(f"  原始总需求: {dp_original['demand'].sum():.2f}")
    print(f"  扩充后总需求: {dp_expanded['demand'].sum():.2f}")
    print(f"  需求量差异: {abs(dp_original['demand'].sum() - dp_expanded['demand'].sum()):.4f}")

    # 空间范围验证
    print(f"\n  原始X范围: [{dp_original['POINT_X'].min():.2f}, {dp_original['POINT_X'].max():.2f}]")
    print(f"  扩充X范围: [{dp_expanded['POINT_X'].min():.2f}, {dp_expanded['POINT_X'].max():.2f}]")
    print(f"  原始Y范围: [{dp_original['POINT_Y'].min():.2f}, {dp_original['POINT_Y'].max():.2f}]")
    print(f"  扩充Y范围: [{dp_expanded['POINT_Y'].min():.2f}, {dp_expanded['POINT_Y'].max():.2f}]")

    # 候选点验证
    print("\n候选点数据:")
    print(f"  原始数量: {len(cp_original)}")
    print(f"  扩充后数量: {len(cp_expanded)}")

    # 候选点空间范围验证
    if 'POINT_X' in cp_original.columns and 'POINT_Y' in cp_original.columns:
        print(f"\n  原始X范围: [{cp_original['POINT_X'].min():.2f}, {cp_original['POINT_X'].max():.2f}]")
        print(f"  扩充X范围: [{cp_expanded['POINT_X'].min():.2f}, {cp_expanded['POINT_X'].max():.2f}]")
        print(f"  原始Y范围: [{cp_original['POINT_Y'].min():.2f}, {cp_original['POINT_Y'].max():.2f}]")
        print(f"  扩充Y范围: [{cp_expanded['POINT_Y'].min():.2f}, {cp_expanded['POINT_Y'].max():.2f}]")

        # 坐标统计对比
        print(f"\n  坐标统计对比:")
        print(f"    POINT_X:")
        print(f"      原始均值: {cp_original['POINT_X'].mean():.4f}")
        print(f"      扩充均值: {cp_expanded['POINT_X'].mean():.4f}")
        print(f"      原始标准差: {cp_original['POINT_X'].std():.4f}")
        print(f"      扩充标准差: {cp_expanded['POINT_X'].std():.4f}")
        print(f"    POINT_Y:")
        print(f"      原始均值: {cp_original['POINT_Y'].mean():.4f}")
        print(f"      扩充均值: {cp_expanded['POINT_Y'].mean():.4f}")
        print(f"      原始标准差: {cp_original['POINT_Y'].std():.4f}")
        print(f"      扩充标准差: {cp_expanded['POINT_Y'].std():.4f}")

    # 检查其他列是否保留
    other_cols = [col for col in cp_original.columns if col not in ['POINT_X', 'POINT_Y']]
    if other_cols:
        print(f"\n  其他列（保留但未插值）: {other_cols[:5]}...")  # 只显示前5个


def save_expanded_data(dp_expanded, cp_expanded, output_dir="data/expanded/"):
    """
    保存扩充后的数据
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    # 保存需求点数据
    dp_output_path = os.path.join(output_dir, "demand_points_10000.shp")
    dp_expanded.to_file(dp_output_path)
    print(f"\n需求点数据已保存到: {dp_output_path}")

    # 保存候选点数据
    cp_output_path = os.path.join(output_dir, "candidate_points_2000.csv")
    cp_expanded.to_csv(cp_output_path, index=False)
    print(f"候选点数据已保存到: {cp_output_path}")


def main():
    """
    主函数：执行完整的数据扩充流程
    """
    print("=" * 50)
    print("数据插值扩充程序")
    print("=" * 50)

    # 1. 加载原始数据
    dp_original, cp_original = load_original_data()

    # 2. 扩充需求点数据
    dp_expanded = expand_demand_points(dp_original, target_count=10000, random_state=42)

    # 3. 扩充候选点数据
    cp_expanded = expand_candidate_points(cp_original, target_count=1000, random_state=42)

    # 4. 验证扩充后的数据
    validate_expanded_data(dp_original, dp_expanded, cp_original, cp_expanded)

    # 5. 保存扩充后的数据
    save_expanded_data(dp_expanded, cp_expanded)

    print("\n" + "=" * 50)
    print("数据扩充完成！")
    print("=" * 50)

    return dp_expanded, cp_expanded


if __name__ == "__main__":
    # 执行主程序
    dp_expanded, cp_expanded = main()

    # 可选：显示扩充后数据的前几行
    print("\n扩充后的需求点数据（前5行）:")
    print(dp_expanded[['POINT_X', 'POINT_Y', 'demand']].head())

    print("\n扩充后的候选点数据（前5行）:")
    # 显示坐标列和其他几列（如果存在）
    display_cols = ['POINT_X', 'POINT_Y']
    other_cols = [col for col in cp_expanded.columns if col not in display_cols][:3]  # 最多显示3个其他列
    display_cols.extend(other_cols)
    print(cp_expanded[display_cols].head())