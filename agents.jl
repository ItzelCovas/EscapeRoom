using Agents
using Random
using LinearAlgebra

#Definicion del agente
@agent struct Ghost(GridAgent{2})
    type::String 
    has_key::Bool
end

#Definicion de la llave
@agent struct Key(GridAgent{2})
    collected::Bool 
end

#Inicializar modelo
function initialize_model(; size=(10,10), num_keys=3)
    space = GridSpace(size; periodic = false, metric = :manhattan)
    model = ABM(Union{Ghost, Key}, space; scheduler=Schedulers.Randomly)

    #Fantasma rastreador
    add_agent!(Ghost, (1,1), model; type="ghost", has_key=false)

    for i in 1:num_keys
        pos=(rand(1:size[1]), rand(1:size[2]))
        add_agent!(Key, pos, model; collected=false)
    end
    return model
end

#Comportamiento del agente
function agent_step!(agent, model)
    if agent isa Ghost
        #Buscar llaves no recolectadas
        keys=[k for k in allagents(model) if k isa Key && !k.collected]

        if !isempty(keys)
            #Encontrar la llave más cerca
            distances=[sqrt(sum((agent.pos .- k.pos).^2)) for k in keys]
            idx=argmin(distances)
            target=keys[idx].pos

            #Calcular direción hacía la llave
            dx=sign(target[1]-agent.pos[1])
            dy=sign(target[2]-agent.pos[2])
            new_pos=(agent.pos[1]+dx, agent.pos[2]+dy)

            #Mover al fantasma si la celda está libre
            if isempty(agents_in_position(model, new_pos))
                move_agent!(agent, new_pos, model)
            end

            #Recolectar la llave
            if agent.pos==target
                keys[idx].collected=true
                agent.has_key=true
                @info "Fantasma ha encontrado una llave en $(agent.pos)"
            end
        else
            #Si no hay llaves
            randomwalk!(agent, model)
        end
    end
end

model = initialize_model()