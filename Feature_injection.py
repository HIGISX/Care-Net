import pandas as pd
import geopandas as gpd


# 定义文件路径
candidate_points_file = './data/EF_data/NEW_Candidate1.csv'
hospitals_file = './data/特征注入/医院转换后POI数据.csv'
parks_file = './data/特征注入/公园转换后POI.csv'
transit_file = './data/特征注入/车站转换后POI数据.csv'
output_file = './data/特征注入/New_Candidate_feature.csv'

# 读取CSV文件
try:
    candidates_df = pd.read_csv(candidate_points_file, encoding='utf-8')
    hospitals_df = pd.read_csv(hospitals_file, encoding='utf-8')
    parks_df = pd.read_csv(parks_file, encoding='utf-8')
    transit_df = pd.read_csv(transit_file, encoding='utf-8')
except UnicodeDecodeError:
    candidates_df = pd.read_csv(candidate_points_file, encoding='gbk')
    hospitals_df = pd.read_csv(hospitals_file, encoding='gbk')
    parks_df = pd.read_csv(parks_file, encoding='gbk')
    transit_df = pd.read_csv(transit_file, encoding='gbk')

# 创建GeoDataFrame，设置坐标系为 EPSG:2382
def create_gdf(df):
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.X, df.Y), crs="EPSG:2382"
    )

candidates_gdf = create_gdf(candidates_df)
hospitals_gdf = create_gdf(hospitals_df)
parks_gdf = create_gdf(parks_df)
transit_gdf = create_gdf(transit_df)

# --- 2. 计算 dist_hospital: 到最近医院的距离 ---

# 使用 sjoin_nearest 直接计算最近点并获取距离
temp_gdf_h = gpd.sjoin_nearest(candidates_gdf, hospitals_gdf, how="left", distance_col="dist_hospital")

# --- 修改点 1 ---
# 使用索引来删除重复项，这是更稳健的方法
# 保留每个原始候选点（由其索引唯一标识）的第一个匹配项
temp_gdf_h = temp_gdf_h[~temp_gdf_h.index.duplicated(keep='first')]

# 将计算出的距离列添加到原始的DataFrame中
# 为了确保顺序正确，我们先按索引排序
temp_gdf_h = temp_gdf_h.sort_index()
candidates_df['dist_hospital'] = temp_gdf_h['dist_hospital'].values


# --- 3. 计算 num_parks_2000m: 2000米内公园数量 ---

# 创建候选点周边的2000米缓冲区
candidates_buffers = candidates_gdf.copy()
candidates_buffers['geometry'] = candidates_buffers.geometry.buffer(2000)

# 空间连接，找出缓冲区内的所有公园
parks_in_buffer = gpd.sjoin(parks_gdf, candidates_buffers, how="inner", predicate="within")

# 按候选点的索引（即原始数据的索引）分组并计数
park_counts = parks_in_buffer.groupby('index_right').size()
park_counts.name = 'num_parks_2000m'

# 将计数结果合并回原始的DataFrame
candidates_df = candidates_df.merge(park_counts, left_index=True, right_index=True, how='left')

# 对于没有公园的区域，填充为0
candidates_df['num_parks_2000m'] = candidates_df['num_parks_2000m'].fillna(0).astype(int)


# --- 4. 计算 dist_transit: 到最近公交站/地铁站的距离 ---

# 同样使用 sjoin_nearest
temp_gdf_t = gpd.sjoin_nearest(candidates_gdf, transit_gdf, how="left", distance_col="dist_transit")

# --- 修改点 2 ---
# 同样使用索引来删除重复项
temp_gdf_t = temp_gdf_t[~temp_gdf_t.index.duplicated(keep='first')]

# 添加到原始DataFrame，同样先排序
temp_gdf_t = temp_gdf_t.sort_index()
candidates_df['dist_transit'] = temp_gdf_t['dist_transit'].values


# --- 5. 保存结果 ---

# 将最终的DataFrame保存为新的CSV文件
candidates_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"计算完成！结果已保存到文件: {output_file}")
print("新添加的列包括: 'dist_hospital', 'num_parks_2000m', 'dist_transit'")
print("\n处理后数据的前5行:")
print(candidates_df.head())