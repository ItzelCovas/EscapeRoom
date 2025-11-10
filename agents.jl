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

            # Verificar límites del espacio
            size = Agents.spacesize(model)
            if 1 <= new_pos[1] <= size[1] && 1 <= new_pos[2] <= size[2]
                # Mover al fantasma si la celda está libre
                if isempty(agents_in_position(new_pos, model))
                    move_agent!(agent, new_pos, model)
                end
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

#Inicializar modelo
function initialize_model(; size=(10,10), num_keys=3)
    space = GridSpace(size; periodic = false, metric = :manhattan)

    # Crear el modelo con agent_step!
    model = StandardABM(
        Union{Ghost, Key}, 
        space; 
        agent_step! = agent_step!,
        scheduler = Schedulers.Randomly()
    )

    #model = ABM(Union{Ghost, Key}, space; scheduler=Schedulers.Randomly)

    # CORRECCIÓN: add_agent! ahora usa la posición directamente
    #add_agent!((1, 1), Ghost, model; type="ghost", has_key=false)

    # CORRECCIÓN: (Tipo, model; kwargs...) sin especificar posición, se asigna automáticamente
    # O especificar posición: add_agent!(model, Tipo; pos=(x,y), kwargs...)
   
    # Crear agentes directamente y agregarlos
    #ghost = Ghost(id=nagents(model)+1, pos=(1, 1), type="ghost", has_key=false)
    # Agregar fantasma en posición (5, 5) - centro del tablero
    ghost = Ghost(1, (5, 5), "ghost", false)
    add_agent_pos!(ghost, model)

    #Fantasma rastreador
    #add_agent!(Ghost, (1,1), model; type="ghost", has_key=false)

    # Agregar llaves en posiciones aleatorias
    for i in 1:num_keys
        placed = false
        while !placed
            pos = (rand(1:size[1]), rand(1:size[2]))
            # Verificar que no haya otro agente en esa posición
            if isempty(agents_in_position(pos, model))
                key = Key(i + 1, pos, false)
                add_agent_pos!(key, model)
                placed = true
            end
        end
    end

    return model
end

#model = initialize_model()