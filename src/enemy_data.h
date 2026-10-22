/* Generated from pinned BK3 scripts and reconstructed native poses. */
static const EnemyFrame garcia_idle[]={
{8,1000,1,0,0},
{8,1001,1,0,0},
{8,1002,1,0,0},
{8,1001,1,0,0},
};
static const EnemyFrame garcia_walk[]={
{8,1000,1,0,0},
{8,1003,1,0,0},
{8,1004,1,0,0},
{8,1003,1,0,0},
};
static const EnemyFrame garcia_held[]={
{99,1005,2,0,0},
};
static const EnemyFrame garcia_hurt2[]={
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
};
static const EnemyFrame garcia_hurt[]={
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
};
static const EnemyFrame garcia_flight[]={
{4,1009,4,0,0},
{99,1012,0,0,0},
};
static const EnemyFrame garcia_floor[]={
{20,1013,0,0,0},
};
static const EnemyFrame garcia_getup[]={
{6,1013,0,0,0},
{6,1014,0,0,0},
{6,1013,0,0,0},
{8,1014,0,0,0},
{10,1011,0,0,0},
{10,1000,1,0,0},
};
static const EnemyFrame garcia_front[]={
{16,1007,2,0,0},
{4,1008,2,0,0},
{6,1018,2,0,0},
{20,1019,2,0,0},
{99,1019,2,0,0},
};
static const EnemyFrame garcia_back[]={
{16,1007,2,0,0},
{4,1008,2,0,0},
{6,1013,0,0,0},
{3,1008,2,0,0},
{99,1013,0,0,0},
};
static const EnemyFrame garcia_jab[]={
{2,1015,1,0,0},
{2,1016,8,0,0},
{4,1017,8,1,1},
{2,1016,8,0,0},
{2,1015,1,0,0},
{2,1000,1,0,0},
};
static const EnemyFrame donovan_idle[]={
{8,1000,1,0,0},
{8,1001,1,0,0},
{8,1002,1,0,0},
{8,1001,1,0,0},
};
static const EnemyFrame donovan_walk[]={
{6,1000,1,0,0},
{6,1003,1,0,0},
{6,1000,1,0,0},
{6,1004,1,0,0},
};
static const EnemyFrame donovan_held[]={
{99,1005,2,0,0},
};
static const EnemyFrame donovan_hurt2[]={
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
{3,1005,2,0,0},
{3,1006,2,0,0},
};
static const EnemyFrame donovan_hurt[]={
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
{3,1009,4,0,0},
{3,1010,4,0,0},
};
static const EnemyFrame donovan_flight[]={
{4,1009,4,0,0},
{99,1012,0,0,0},
};
static const EnemyFrame donovan_floor[]={
{20,1013,0,0,0},
};
static const EnemyFrame donovan_getup[]={
{4,1013,0,0,0},
{4,1014,0,0,0},
{4,1013,0,0,0},
{6,1014,0,0,0},
{8,1011,0,0,0},
{10,1000,1,0,0},
};
static const EnemyFrame donovan_front[]={
{16,1007,2,0,0},
{4,1008,2,0,0},
{6,1026,2,0,0},
{20,1027,2,0,0},
{99,1027,2,0,0},
};
static const EnemyFrame donovan_back[]={
{16,1007,2,0,0},
{4,1008,2,0,0},
{6,1013,0,0,0},
{3,1008,2,0,0},
{99,1013,0,0,0},
};
static const EnemyFrame donovan_jab[]={
{2,1000,1,0,0},
{2,1023,1,0,0},
{2,1024,11,0,0},
{4,1025,11,1,1},
{2,1024,11,0,0},
{2,1023,1,0,0},
};
static const EnemyFrame donovan_uppercut[]={
{2,1000,1,0,0},
{2,1019,8,0,0},
{3,1020,9,0,0},
{2,1021,9,3,136},
{3,1021,9,0,0},
{20,1022,10,4,136},
};
static const EnemyFrame donovan_kick[]={
{2,1000,1,0,0},
{3,1015,5,0,0},
{4,1016,6,0,0},
{5,1017,7,2,132},
{18,1018,7,0,0},
};
static const EnemyFrame *const enemy_sequences[2][13]={
{garcia_idle,garcia_walk,garcia_held,garcia_hurt2,garcia_hurt,garcia_flight,garcia_floor,garcia_getup,garcia_front,garcia_back,garcia_jab,garcia_jab,garcia_jab},
{donovan_idle,donovan_walk,donovan_held,donovan_hurt2,donovan_hurt,donovan_flight,donovan_floor,donovan_getup,donovan_front,donovan_back,donovan_jab,donovan_uppercut,donovan_kick},
};
static const unsigned char enemy_sizes[2][13]={
{4,4,1,10,10,2,1,6,5,5,6,6,6},
{4,4,1,10,10,2,1,6,5,5,6,6,5},
};
