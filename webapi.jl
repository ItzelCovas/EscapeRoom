include("agents.jl")
using Genie, Genie.Renderer.Json, Genie.Requests, HTTP
using UUIDs

println("Inicializando modelo...")
model = initialize_model()
println("Modelo creado con éxito")

# Inicializar/actualizar llaves desde Python
route("/init_keys", method = POST) do
    try
        payload = jsonpayload()
        key_positions = payload["keys"]  # Lista de tuplas [(x,y), (x,y), ...]
        
        # Limpiar modelo actual
        global model
        model = initialize_model(key_positions=[(Int(k[1]), Int(k[2])) for k in key_positions])
        
        @info "🔑 Llaves inicializadas (escondidas): $key_positions"
        json(Dict("status" => "ok", "keys" => key_positions))
    catch e
        @error "Error en /init_keys" exception=e
        json(Dict("error" => string(e)))
    end
end

# **NUEVA RUTA**: Hacer visible una llave escondida
route("/reveal_key", method = POST) do
    try
        payload = jsonpayload()
        key_pos = (Int(payload["x"]), Int(payload["y"]))
        
        # Encontrar y revelar la llave
        for agent in allagents(model)
            if agent isa Key && agent.pos == key_pos && agent.is_hidden
                agent.is_hidden = false
                agent.is_visible = true
                @info "🔍 Llave en $key_pos ahora es VISIBLE (fantasma la perseguirá)"
                break
            end
        end
        
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /reveal_key" exception=e
        json(Dict("error" => string(e)))
    end
end

# Actualizar estado: llave recolectada
route("/collect_key", method = POST) do
    try
        payload = jsonpayload()
        key_pos = (Int(payload["x"]), Int(payload["y"]))
        
        # Marcar la llave como recolectada
        for agent in allagents(model)
            if agent isa Key && agent.pos == key_pos
                agent.is_visible = false
                agent.is_collected = true
                @info "Llave en $key_pos RECOLECTADA (fantasma dejará de perseguirla)"
                break
            end
        end
        
        json(Dict("status" => "ok"))
    catch e
        @error "Error en /collect_key" exception=e
        json(Dict("error" => string(e)))
    end
end

# Ruta principal que Python consulta
route("/update") do
    try
        # Avanzar un paso en la simulación
        step!(model, 1)
        
        # Obtener posiciones de fantasmas y llaves
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        # SOLO devolver llaves visibles (no escondidas, no recolectadas)
        keys = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]

        # Retornar JSON
        json(Dict(
            "ghosts" => ghosts,
            "keys" => keys
        ))
    catch e
        @error "Error en /update" exception=e
        json(Dict("error" => string(e)))
    end
end

# Ruta adicional para verificar el estado sin avanzar
route("/status") do
    try
        ghosts = [Tuple(a.pos) for a in allagents(model) if a isa Ghost]
        keys_visible = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_visible && !a.is_collected]
        keys_hidden = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_hidden]
        keys_collected = [Tuple(a.pos) for a in allagents(model) if a isa Key && a.is_collected]

        json(Dict(
            "ghosts" => ghosts,
            "keys_visible" => keys_visible,
            "keys_hidden" => keys_hidden,
            "keys_collected" => keys_collected
        ))
    catch e
        @error "Error en /status" exception=e
        json(Dict("error" => string(e)))
    end
end

Genie.config.run_as_server = true
Genie.config.cors_headers["Access-Control-Allow-Origin"] = "*"
Genie.config.cors_headers["Access-Control-Allow-Headers"] = "Content-Type"
Genie.config.cors_headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
Genie.config.cors_allowed_origins = ["*"]

up(8000, host="0.0.0.0")