library('dplyr')
library('igraph')

library("optparse")
 
option_list = list(
    make_option(c("--graph"), type="character", default=NULL, 
              help="graph ml file", metavar="character"),
    make_option(c("--stations"), type="character", default=NULL, 
              help="station-to-station mapping", metavar="character"),
    make_option(c("--gtfsmapping"), type="character", default=NULL, 
              help="Platform to GTFS stop ID mapping", metavar="character"),
    make_option(c("--stops"), type="character", default=NULL, 
              help="Stop IDs", metavar="character")
    
); 
 
opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser);

h <- read_graph(opt$graph,format = 'graphml')

V(h)$clean_name <- V(h)$name
V(h)$name <- V(h)$id

h_el <- igraph::as_data_frame(h)
h_el$line <- NA

vertex_attributes <- data.frame(name=V(h)$id,clean_name=V(h)$clean_name,label=V(h)$label,node_type=V(h)$node_type,station=V(h)$station,color=V(h)$color,stringsAsFactors = F)

ss <- read.csv(opt$stations,stringsAsFactors = F)
p_gtfs <- read.csv(opt$gtfsmapping,stringsAsFactors = F)
stops <- read.csv(opt$stops,stringsAsFactors = F)

station_connections <- left_join(ss[,c('from','to','line')],p_gtfs[,c('platform_id','stop_id','line')],by = c('from'='stop_id',"line"="line"))
colnames(station_connections)[4] <- 'from_pid'
station_connections <- left_join(station_connections,p_gtfs[,c('platform_id','stop_id','line')],by = c('to'='stop_id',"line"="line"))
colnames(station_connections)[5] <- 'to_pid'

## filling stations without accessible platforms to have GTFS stop ID as the node
station_connections[is.na(station_connections$from_pid),"from_pid"] <- station_connections$from[is.na(station_connections$from_pid)]
station_connections[is.na(station_connections$to_pid),"to_pid"] <- station_connections$to[is.na(station_connections$to_pid)]

gtfs_ids <- unique(c(ss$from,ss$to))
gtfs_attributes <- data.frame(name=gtfs_ids,clean_name=gtfs_ids,label=gtfs_ids,node_type='GTFS Stop ID',station=stops$stop_name[stops$stop_id %in% gtfs_ids],color='darkgrey')

vertex_attributes<- rbind(vertex_attributes,gtfs_attributes)

addl_edges <- station_connections[!duplicated(station_connections),c('from_pid','to_pid','line')]
colnames(addl_edges) <- c("from","to",'line')

addl_edges <- addl_edges %>% left_join(vertex_attributes[,c('name','label')],by=c("from"='label')) %>% left_join(vertex_attributes[,c('name','label')],by=c("to"='label'))
addl_edges <- addl_edges[,c('name.x','name.y','line')]
colnames(addl_edges) <- c("from","to","line")

full_edgelist <- rbind(h_el,addl_edges)
h_new <- graph_from_data_frame(full_edgelist,directed = F)

df <- igraph::as_data_frame(h_new,'both')

df$vertices <- df$vertices %>% 
  left_join(vertex_attributes, by='name')

updated_graph <- graph_from_data_frame(df$edges,
                                   directed = F,
                                   vertices = df$vertices)

names(vertex_attr(updated_graph))[which(names(vertex_attr(updated_graph)) == "name")] <- "id"
names(vertex_attr(updated_graph))[which(names(vertex_attr(updated_graph)) == "clean_name")] <- "name"

write.graph(updated_graph,opt$graph,format='graphml')